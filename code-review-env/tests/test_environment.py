"""Tests for CodeReviewEnv reset/step behavior."""

from __future__ import annotations

from env.environment import CodeReviewEnv
from env.models import CodeReviewAction


def test_reset_returns_observation() -> None:
    """reset() returns a valid observation with empty comments."""

    env = CodeReviewEnv()
    obs = env.reset("easy")
    assert obs.task_id == "easy"
    assert obs.language == "python"
    assert obs.step_number == 1
    assert obs.max_steps == 8
    assert obs.existing_comments == []


def test_reset_twice_clears_state() -> None:
    """reset() called twice returns clean state with zero comments."""

    env = CodeReviewEnv()
    env.reset("easy")
    obs2 = env.reset("easy")
    assert obs2.existing_comments == []
    assert obs2.step_number == 1


def test_step_add_comment_near_bug_positive_reward() -> None:
    """Valid add_comment near real bug yields positive reward."""

    env = CodeReviewEnv()
    env.reset("easy")
    action = CodeReviewAction(operation="add_comment", line_number=18, severity="major", category="bug", message="Index error risk")
    obs, reward, done, info = env.step(action)
    assert reward > 0.0
    assert done is False
    assert info["bugs_found"] >= 1
    assert len(obs.existing_comments) == 1


def test_step_add_comment_false_positive_negative_reward() -> None:
    """add_comment on a non-bug line yields negative reward."""

    env = CodeReviewEnv()
    env.reset("easy")
    action = CodeReviewAction(operation="add_comment", line_number=2, severity="minor", category="style", message="Nit")
    _, reward, _, info = env.step(action)
    assert reward == 0.01
    assert info["false_positives"] >= 1


def test_step_duplicate_comment_negative_reward() -> None:
    """Duplicate comment on same bug yields negative reward."""

    env = CodeReviewEnv()
    env.reset("easy")
    a1 = CodeReviewAction(operation="add_comment", line_number=18, severity="major", category="bug", message="Bug")
    _, r1, _, _ = env.step(a1)
    assert r1 > 0.0
    a2 = CodeReviewAction(operation="add_comment", line_number=19, severity="major", category="bug", message="Duplicate")
    _, r2, _, _ = env.step(a2)
    assert r2 == 0.01


def test_approve_with_unfound_critical_or_major_penalty() -> None:
    """approve() when major bugs exist yields large negative reward."""

    env = CodeReviewEnv()
    env.reset("medium")
    obs, reward, done, info = env.step(CodeReviewAction(operation="approve", summary="LGTM"))
    assert done is True
    assert reward == 0.01
    assert info["current_score"] == 0.001


def test_done_returns_final_grader_score() -> None:
    """done triggers grader and returns final score reward."""

    env = CodeReviewEnv()
    env.reset("easy")
    env.step(CodeReviewAction(operation="add_comment", line_number=18, severity="major", category="bug", message="Bug 1"))
    obs, reward, done, info = env.step(CodeReviewAction(operation="done"))
    assert done is True
    assert reward >= 0.0
    assert isinstance(info["current_score"], float)
    assert obs.review_status == "submitted"


def test_step_number_increments_and_episode_ends_at_max_steps() -> None:
    """step_number increments and episode ends at max steps."""

    env = CodeReviewEnv()
    obs = env.reset("easy")
    assert obs.step_number == 1
    done = False
    for _ in range(8):
        obs, _, done, _ = env.step(CodeReviewAction(operation="add_comment", line_number=2, severity="minor", category="style", message="x"))
        if done:
            break
    assert done is True

