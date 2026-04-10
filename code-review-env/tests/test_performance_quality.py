"""Performance, stress, and quality tests for the code-review environment.

These tests are designed to be deterministic and CI-friendly while still
covering wider ranges of behavior and runtime expectations.
"""

from __future__ import annotations

import statistics
import time

from fastapi.testclient import TestClient

from env.environment import CodeReviewEnv
from env.models import CodeReviewAction
from server import app


def test_env_reset_and_step_latency_budget() -> None:
    """Environment reset/step operations stay within practical latency budgets."""

    env = CodeReviewEnv()
    reset_times = []
    step_times = []

    for _ in range(40):
        t0 = time.perf_counter()
        env.reset("easy")
        reset_times.append(time.perf_counter() - t0)

        t1 = time.perf_counter()
        env.step(CodeReviewAction(operation="add_comment", line_number=18, severity="major", category="bug", message="x"))
        step_times.append(time.perf_counter() - t1)

    assert statistics.mean(reset_times) < 0.05
    assert statistics.mean(step_times) < 0.05
    assert max(reset_times) < 0.30
    assert max(step_times) < 0.30


def test_api_endpoint_stability_under_repeated_requests() -> None:
    """API remains stable over many sequential requests."""

    client = TestClient(app)
    statuses = []

    for _ in range(30):
        r0 = client.post("/reset", json={"task_id": "easy"})
        statuses.append(r0.status_code)
        r1 = client.post(
            "/step",
            json={
                "operation": "add_comment",
                "line_number": 18,
                "severity": "major",
                "category": "bug",
                "message": "possible off-by-one",
            },
        )
        statuses.append(r1.status_code)
        r2 = client.get("/state")
        statuses.append(r2.status_code)

    assert all(code == 200 for code in statuses)


def test_long_horizon_mixed_actions_keeps_state_consistent() -> None:
    """Long mixed-action episode preserves state invariants."""

    env = CodeReviewEnv()
    env.reset("hard")

    actions = [
        CodeReviewAction(operation="add_comment", line_number=25, severity="major", category="performance", message="n+1"),
        CodeReviewAction(operation="add_comment", line_number=29, severity="critical", category="bug", message="race"),
        CodeReviewAction(operation="add_comment", line_number=32, severity="nit", category="style", message="trap"),
        CodeReviewAction(operation="add_comment", line_number=34, severity="major", category="bug", message="except pass"),
        CodeReviewAction(operation="request_changes", summary="found issues"),
    ]

    done = False
    for act in actions:
        _, _, done, info = env.step(act)
        if done:
            break

    state = env.state()
    assert state["step_number"] >= 2
    assert isinstance(state["comments"], list)
    assert state["bugs_found"] >= 0
    assert state["false_positives"] >= 0
    assert isinstance(info["current_score"], float)


def test_reward_signal_is_not_constant_across_behavior_patterns() -> None:
    """Reward trajectory changes with behavior quality (non-constant signal)."""

    env = CodeReviewEnv()

    env.reset("medium")
    rewards_a = []
    for line in (1, 2, 3):
        _, r, _, _ = env.step(CodeReviewAction(operation="add_comment", line_number=line, severity="minor", category="style", message="noise"))
        rewards_a.append(r)
    _, r_done_a, _, _ = env.step(CodeReviewAction(operation="done"))
    rewards_a.append(r_done_a)

    env.reset("medium")
    rewards_b = []
    for payload in (
        (20, "major", "security", "secret"),
        (21, "critical", "security", "sqli"),
        (26, "critical", "security", "idor"),
    ):
        _, r, _, _ = env.step(
            CodeReviewAction(
                operation="add_comment",
                line_number=payload[0],
                severity=payload[1],
                category=payload[2],
                message=payload[3],
            )
        )
        rewards_b.append(r)
    _, r_done_b, _, _ = env.step(CodeReviewAction(operation="done"))
    rewards_b.append(r_done_b)

    assert rewards_a != rewards_b
    assert sum(rewards_b) != sum(rewards_a)

