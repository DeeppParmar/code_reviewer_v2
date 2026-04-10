"""Comprehensive integration tests across tasks, rewards, and determinism."""

from __future__ import annotations

from env.environment import CodeReviewEnv
from env.models import CodeReviewAction


def test_each_task_reset_and_done_path_is_stable() -> None:
    """Each task can reset and reach done with a valid score."""

    env = CodeReviewEnv()
    for task_id in ("easy", "medium", "hard"):
        obs = env.reset(task_id)
        assert obs.task_id == task_id
        assert obs.step_number == 1
        assert obs.max_steps >= 1

        env.step(CodeReviewAction(operation="add_comment", line_number=1, severity="minor", category="style", message="probe"))
        obs2, reward, done, info = env.step(CodeReviewAction(operation="done"))
        assert done is True
        assert obs2.review_status == "submitted"
        assert 0.0 <= float(reward) <= 1.1
        assert isinstance(info["current_score"], float)


def test_done_is_deterministic_for_same_comment_set() -> None:
    """Running done twice with identical actions yields identical final reward."""

    def run_once() -> float:
        env = CodeReviewEnv()
        env.reset("hard")
        env.step(CodeReviewAction(operation="add_comment", line_number=25, severity="major", category="performance", message="n+1"))
        _, reward, _, _ = env.step(CodeReviewAction(operation="done"))
        return float(reward)

    r1 = run_once()
    r2 = run_once()
    assert r1 == r2


def test_step_limit_penalty_applies_when_exceeded_without_done() -> None:
    """Exceeding max steps without done triggers final penalty."""

    env = CodeReviewEnv()
    obs = env.reset("easy")
    max_steps = obs.max_steps
    done = False
    for _ in range(max_steps + 2):
        obs, _, done, info = env.step(
            CodeReviewAction(operation="add_comment", line_number=2, severity="minor", category="style", message="x")
        )
        if done:
            break

    assert done is True
    assert info["current_score"] == 0.001

