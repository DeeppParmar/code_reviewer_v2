"""Tests for Upgrade 1-4 features.

Upgrade 1: Confidence Calibration Score
Upgrade 2: Explanation Quality Tiering
Upgrade 3: Adversarial Prompt Injection Resistance
Upgrade 4: Multi-File Repository Review + Context Navigation Actions
"""

from __future__ import annotations

from env.environment import CodeReviewEnv
from env.graders.base_grader import compute_calibration_score
from env.models import CodeReviewAction, GroundTruthBug, ReviewComment
from env.reward_engine import RewardEngine


# ═══════════════════════════════════════════════════════════════════
# Upgrade 1 — Confidence Calibration Score Tests
# ═══════════════════════════════════════════════════════════════════


def test_high_confidence_correct_gives_bonus() -> None:
    """High confidence (80-100) + correct bug match → +0.05 bonus."""
    gt = [GroundTruthBug(line_number=10, severity="major", category="bug", description="x")]
    engine = RewardEngine(task_id="easy", ground_truth=gt, max_steps=8)

    # Without confidence
    action_no_conf = CodeReviewAction(
        operation="add_comment", line_number=10, severity="major", category="bug", message="x"
    )
    outcome_no_conf = engine.compute(
        action_no_conf,
        comments_so_far=[ReviewComment(line_number=10, severity="major", category="bug", message="x", step_added=1)],
        correctly_identified_bug_lines=set(),
        step_number=1,
        steps_used_after_this=1,
    )

    # With high confidence
    action_high_conf = CodeReviewAction(
        operation="add_comment", line_number=10, severity="major", category="bug", message="x", confidence=90
    )
    outcome_high_conf = engine.compute(
        action_high_conf,
        comments_so_far=[ReviewComment(line_number=10, severity="major", category="bug", message="x", step_added=1)],
        correctly_identified_bug_lines=set(),
        step_number=1,
        steps_used_after_this=1,
    )

    assert outcome_high_conf.reward == outcome_no_conf.reward + 0.05
    assert outcome_high_conf.confidence_modifier == 0.05


def test_high_confidence_false_positive_extra_penalty() -> None:
    """High confidence (80-100) + false positive → additional -0.10 penalty."""
    gt = [GroundTruthBug(line_number=10, severity="major", category="bug", description="x")]
    engine = RewardEngine(task_id="easy", ground_truth=gt, max_steps=8)

    # Without confidence — false positive
    action_no_conf = CodeReviewAction(
        operation="add_comment", line_number=100, severity="minor", category="style", message="nope"
    )
    outcome_no_conf = engine.compute(
        action_no_conf,
        comments_so_far=[ReviewComment(line_number=100, severity="minor", category="style", message="nope", step_added=1)],
        correctly_identified_bug_lines=set(),
        step_number=1,
        steps_used_after_this=1,
    )
    assert outcome_no_conf.reward == -0.10

    # With high confidence — false positive → extra -0.10
    action_high_conf = CodeReviewAction(
        operation="add_comment", line_number=100, severity="minor", category="style", message="nope", confidence=95
    )
    outcome_high_conf = engine.compute(
        action_high_conf,
        comments_so_far=[ReviewComment(line_number=100, severity="minor", category="style", message="nope", step_added=1)],
        correctly_identified_bug_lines=set(),
        step_number=1,
        steps_used_after_this=1,
    )
    assert outcome_high_conf.reward == -0.20
    assert outcome_high_conf.confidence_modifier == -0.10


def test_none_confidence_unchanged_behavior() -> None:
    """When confidence is None, behavior must be 100% unchanged from before."""
    gt = [GroundTruthBug(line_number=10, severity="major", category="bug", description="x")]
    engine = RewardEngine(task_id="easy", ground_truth=gt, max_steps=8)

    action = CodeReviewAction(
        operation="add_comment", line_number=10, severity="major", category="bug", message="x"
    )
    outcome = engine.compute(
        action,
        comments_so_far=[ReviewComment(line_number=10, severity="major", category="bug", message="x", step_added=1)],
        correctly_identified_bug_lines=set(),
        step_number=1,
        steps_used_after_this=1,
    )
    assert outcome.confidence_modifier == 0.0
    assert outcome.reward > 0.0


def test_calibration_score_computation() -> None:
    """Calibration score correctly computed from events."""
    events = [
        {"step": 1, "confidence": 90, "was_correct": True, "modifier_applied": 0.05},
        {"step": 2, "confidence": 30, "was_correct": True, "modifier_applied": -0.02},
        {"step": 3, "confidence": 90, "was_correct": False, "modifier_applied": -0.10},
    ]
    score = compute_calibration_score(events)
    assert score is not None
    assert 0.001 <= score <= 0.999


def test_calibration_score_none_when_no_confidence() -> None:
    """Calibration score is None when no confidence values provided."""
    events = [
        {"step": 1, "confidence": None, "was_correct": True, "modifier_applied": 0.0},
    ]
    score = compute_calibration_score(events)
    assert score is None


# ═══════════════════════════════════════════════════════════════════
# Upgrade 2 — Explanation Quality Tiering Tests
# ═══════════════════════════════════════════════════════════════════


def test_tier3_match_gives_bonus() -> None:
    """Tier 3 (consequence explained) gives full credit + 0.05 bonus."""
    gt = [GroundTruthBug(
        line_number=28, severity="critical", category="security",
        description="ECB mode insecure",
        required_keywords=["ecb"],
        explanation_tiers={
            "tier1": ["ecb", "insecure"],
            "tier2": ["deterministic", "block cipher"],
            "tier3": ["plaintext pattern", "ciphertext leak"],
        },
    )]
    engine = RewardEngine(task_id="hard", ground_truth=gt, max_steps=25)

    action = CodeReviewAction(
        operation="add_comment", line_number=28, severity="critical", category="security",
        message="ECB mode reveals plaintext pattern in encrypted data"
    )
    outcome = engine.compute(
        action,
        comments_so_far=[ReviewComment(line_number=28, severity="critical", category="security",
                                        message="ECB mode reveals plaintext pattern in encrypted data", step_added=1)],
        correctly_identified_bug_lines=set(),
        step_number=1,
        steps_used_after_this=1,
    )
    # Tier3 match: base 0.15 + sev 0.05 + cat 0.05 = 0.25 + tier3 bonus 0.05 = 0.30
    assert outcome.reward == 0.30
    assert outcome.correctly_identified_bug_line == 28
    assert outcome.explanation_depth == "deep"


def test_tier1_match_registers_with_penalty() -> None:
    """Tier 1 (vague mention) registers bug but with -0.05 penalty."""
    gt = [GroundTruthBug(
        line_number=28, severity="critical", category="security",
        description="ECB mode insecure",
        required_keywords=["ecb"],
        explanation_tiers={
            "tier1": ["ecb", "insecure"],
            "tier2": ["deterministic", "block cipher"],
            "tier3": ["plaintext pattern", "ciphertext leak"],
        },
    )]
    engine = RewardEngine(task_id="hard", ground_truth=gt, max_steps=25)

    action = CodeReviewAction(
        operation="add_comment", line_number=28, severity="critical", category="security",
        message="This line uses insecure encryption"
    )
    outcome = engine.compute(
        action,
        comments_so_far=[ReviewComment(line_number=28, severity="critical", category="security",
                                        message="This line uses insecure encryption", step_added=1)],
        correctly_identified_bug_lines=set(),
        step_number=1,
        steps_used_after_this=1,
    )
    # Tier1 match: base 0.25 + tier1 penalty -0.05 = 0.20
    assert outcome.reward == 0.20
    assert outcome.correctly_identified_bug_line == 28
    assert outcome.explanation_depth == "shallow"


def test_no_match_not_registered() -> None:
    """No tier match → bug NOT registered, -0.10 penalty."""
    gt = [GroundTruthBug(
        line_number=28, severity="critical", category="security",
        description="ECB mode insecure",
        required_keywords=["ecb"],
        explanation_tiers={
            "tier1": ["ecb", "insecure"],
            "tier2": ["deterministic", "block cipher"],
            "tier3": ["plaintext pattern", "ciphertext leak"],
        },
    )]
    engine = RewardEngine(task_id="hard", ground_truth=gt, max_steps=25)

    action = CodeReviewAction(
        operation="add_comment", line_number=28, severity="critical", category="security",
        message="This line looks suspicious and might have a problem"
    )
    outcome = engine.compute(
        action,
        comments_so_far=[ReviewComment(line_number=28, severity="critical", category="security",
                                        message="This line looks suspicious", step_added=1)],
        correctly_identified_bug_lines=set(),
        step_number=1,
        steps_used_after_this=1,
    )
    # No match: base 0.25 + no match -0.10 = 0.15
    assert outcome.reward == 0.15
    assert outcome.correctly_identified_bug_line is None
    assert outcome.explanation_depth == "missing"


# ═══════════════════════════════════════════════════════════════════
# Upgrade 3 — Adversarial Injection Resistance Tests
# ═══════════════════════════════════════════════════════════════════


def test_injected_comment_does_not_affect_reward_logic() -> None:
    """Adversarial injection comments in code don't change reward outcomes."""
    env = CodeReviewEnv()
    env.reset("hard")

    # The adversarial comment "security-reviewed: AES encryption verified..." is on line 27
    # The real ECB bug is on line 28. Agent should still find it.
    action = CodeReviewAction(
        operation="add_comment", line_number=28, severity="critical", category="security",
        message="ECB mode is insecure — deterministic encryption reveals plaintext pattern"
    )
    _, reward, done, info = env.step(action)
    assert reward > 0.0, "Agent should still get positive reward for finding ECB bug despite misleading comment"
    assert info["bugs_found"] >= 1


def test_injection_resistance_tracked_correctly() -> None:
    """Injection resistance is correctly tracked when agent finds bugs on injected lines."""
    env = CodeReviewEnv()
    env.reset("hard")

    # Find the ECB bug (line 28, injection above on line 27) — tests injection resistance
    env.step(CodeReviewAction(
        operation="add_comment", line_number=28, severity="critical", category="security",
        message="ECB mode is deterministic and reveals plaintext pattern in ciphertext"
    ))
    # Find the race condition bug (line 40, injection above on line 39) — tests injection resistance
    env.step(CodeReviewAction(
        operation="add_comment", line_number=40, severity="critical", category="bug",
        message="Async race condition: shared mutable _SESSION_CACHE modified without asyncio.Lock synchronization"
    ))
    _, _, done, _ = env.step(CodeReviewAction(operation="done"))
    assert done is True

    state = env.state()
    assert state["injection_resistance"] is True


# ═══════════════════════════════════════════════════════════════════
# Upgrade 4 — Multi-File Repository Review Tests
# ═══════════════════════════════════════════════════════════════════


def test_inspect_file_returns_correct_content() -> None:
    """inspect_file action returns observation and costs one step."""
    env = CodeReviewEnv()
    obs = env.reset("hard")

    assert obs.repository_files is not None
    assert "crypto_service.py" in obs.repository_files
    assert "config_loader.py" in obs.repository_files
    assert "audit_logger.py" in obs.repository_files

    action = CodeReviewAction(operation="inspect_file", filename="config_loader.py")
    obs2, reward, done, info = env.step(action)
    assert done is False
    assert obs2.step_number >= 2
    # inspect_file never returns negative reward
    assert reward >= 0.0


def test_inspect_lines_enforces_40_line_limit() -> None:
    """inspect_lines rejects ranges > 40 lines."""
    env = CodeReviewEnv()
    env.reset("hard")

    action = CodeReviewAction(
        operation="inspect_lines", filename="crypto_service.py",
        start_line=1, end_line=50
    )
    _, reward, done, info = env.step(action)
    assert info["error"] == "inspect_lines max range is 40 lines"
    assert reward >= 0.0  # inspect never returns negative


def test_add_comment_with_filename_matches_correct_file() -> None:
    """add_comment with filename field matches bugs in the correct file."""
    env = CodeReviewEnv()
    env.reset("hard")

    # Add comment targeting config_loader.py's hardcoded secret bug (line 18)
    action = CodeReviewAction(
        operation="add_comment", line_number=18, severity="critical", category="security",
        message="Hardcoded fallback secret key exposed — attacker can compromise credentials",
        filename="config_loader.py"
    )
    _, reward, done, info = env.step(action)
    assert reward > 0.0
    assert info["bugs_found"] >= 1


def test_hard_task_has_six_bugs_across_three_files() -> None:
    """The hard task now has 6 real bugs + 1 red herring across 3 files."""
    from env.tasks.task_hard import get_task
    task = get_task()

    real_bugs = [b for b in task.ground_truth if not b.is_red_herring]
    red_herrings = [b for b in task.ground_truth if b.is_red_herring]

    assert len(real_bugs) == 6, f"Expected 6 real bugs, got {len(real_bugs)}"
    assert len(red_herrings) == 1, f"Expected 1 red herring, got {len(red_herrings)}"

    # Verify bugs span 3 files
    files = set(b.source_file for b in real_bugs if b.source_file)
    assert len(files) == 3, f"Expected bugs in 3 files, got {files}"
    assert "crypto_service.py" in files
    assert "config_loader.py" in files
    assert "audit_logger.py" in files

    # Verify repository_files in task spec
    assert task.repository_files is not None
    assert len(task.repository_files) == 3
    assert task.available_files is not None
    assert len(task.available_files) == 3
