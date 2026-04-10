"""Tests for reward shaping in RewardEngine."""

from __future__ import annotations

from env.models import CodeReviewAction, GroundTruthBug, ReviewComment
from env.reward_engine import RewardEngine


def test_add_comment_near_real_bug_positive() -> None:
    """Near-bug comment yields positive reward."""

    gt = [GroundTruthBug(line_number=10, severity="major", category="bug", description="x")]
    engine = RewardEngine(task_id="easy", ground_truth=gt, max_steps=8)
    action = CodeReviewAction(operation="add_comment", line_number=10, severity="major", category="bug", message="x")
    outcome = engine.compute(
        action,
        comments_so_far=[ReviewComment(line_number=10, severity="major", category="bug", message="x", step_added=1)],
        correctly_identified_bug_lines=set(),
        step_number=1,
        steps_used_after_this=1,
    )
    assert outcome.reward > 0.0


def test_add_comment_on_red_herring_is_minus_point_two() -> None:
    """Flagging red herring yields -0.20."""

    gt = [GroundTruthBug(line_number=10, severity="nit", category="style", description="trap", is_red_herring=True)]
    engine = RewardEngine(task_id="hard", ground_truth=gt, max_steps=25)
    action = CodeReviewAction(operation="add_comment", line_number=10, severity="nit", category="style", message="trap")
    outcome = engine.compute(
        action,
        comments_so_far=[ReviewComment(line_number=10, severity="nit", category="style", message="trap", step_added=1)],
        correctly_identified_bug_lines=set(),
        step_number=1,
        steps_used_after_this=1,
    )
    assert outcome.reward == -0.20


def test_add_comment_false_positive_is_minus_point_one() -> None:
    """False positive yields -0.10."""

    gt = [GroundTruthBug(line_number=10, severity="major", category="bug", description="x")]
    engine = RewardEngine(task_id="easy", ground_truth=gt, max_steps=8)
    action = CodeReviewAction(operation="add_comment", line_number=100, severity="minor", category="style", message="nope")
    outcome = engine.compute(
        action,
        comments_so_far=[ReviewComment(line_number=100, severity="minor", category="style", message="nope", step_added=1)],
        correctly_identified_bug_lines=set(),
        step_number=1,
        steps_used_after_this=1,
    )
    assert outcome.reward == -0.10


def test_approve_with_unfound_critical_bugs_is_minus_point_five() -> None:
    """Approving with remaining critical/major bugs yields -0.50."""

    gt = [GroundTruthBug(line_number=10, severity="critical", category="security", description="x")]
    engine = RewardEngine(task_id="medium", ground_truth=gt, max_steps=15)
    action = CodeReviewAction(operation="approve", summary="ok")
    outcome = engine.compute(
        action,
        comments_so_far=[],
        correctly_identified_bug_lines=set(),
        step_number=1,
        steps_used_after_this=1,
    )
    assert outcome.reward == -0.50


def test_efficiency_bonus_triggers() -> None:
    """Efficiency bonus triggers when under 60% steps and score > 0.8."""

    gt = [GroundTruthBug(line_number=10, severity="major", category="bug", description="x")]
    engine = RewardEngine(task_id="easy", ground_truth=gt, max_steps=10)
    comments = [ReviewComment(line_number=10, severity="major", category="bug", message="x", step_added=1)]
    action = CodeReviewAction(operation="done")
    outcome = engine.compute(
        action,
        comments_so_far=comments,
        correctly_identified_bug_lines={10},
        step_number=2,
        steps_used_after_this=2,
    )
    assert outcome.final_score == 0.999
    assert outcome.reward == 1.099

