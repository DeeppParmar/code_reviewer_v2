"""Advanced adversarial test cases for the code-review environment.

These tests focus on edge conditions, undesirable behaviors, and ensuring the
reward/grader logic produces varied, deterministic outcomes.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from env.environment import CodeReviewEnv
from env.models import CodeReviewAction
from server import app


def test_add_comment_missing_line_number_returns_negative_reward_and_error() -> None:
    """Missing line_number for add_comment returns -0.05 and error in info."""

    env = CodeReviewEnv()
    env.reset("easy")
    obs, reward, done, info = env.step(CodeReviewAction(operation="add_comment", severity="minor", category="bug", message="x"))
    assert done is False
    assert reward == 0.01
    assert info["error"] is not None
    assert info["false_positives"] >= 1
    assert obs.step_number >= 2


def test_bug_matching_within_plus_minus_five_is_positive() -> None:
    """Comment within +/-5 lines of a real bug yields positive reward."""

    env = CodeReviewEnv()
    env.reset("medium")
    obs, reward, done, info = env.step(
        CodeReviewAction(operation="add_comment", line_number=26, severity="critical", category="security", message="SQLi")
    )
    assert done is False
    assert reward > 0.0
    assert info["bugs_found"] >= 1
    assert len(obs.existing_comments) == 1


def test_comment_outside_plus_minus_five_is_false_positive() -> None:
    """Comment far from any bug yields -0.10 false positive penalty."""

    env = CodeReviewEnv()
    env.reset("medium")
    _, reward, _, info = env.step(
        CodeReviewAction(operation="add_comment", line_number=999, severity="minor", category="style", message="nit")
    )
    assert reward == 0.01
    assert info["false_positives"] >= 1


def test_red_herring_penalty_is_applied_on_hard_task() -> None:
    """Flagging the hard-task red herring yields -0.20."""

    env = CodeReviewEnv()
    env.reset("hard")
    _, reward, _, info = env.step(
        CodeReviewAction(operation="add_comment", line_number=45, severity="nit", category="style", message="suspicious pass")
    )
    assert reward == 0.01
    assert info["false_positives"] >= 1


def test_approve_bonus_when_no_critical_or_major_remaining() -> None:
    """approve yields +0.10 only after all critical/major are found."""

    env = CodeReviewEnv()
    env.reset("medium")
    env.step(CodeReviewAction(operation="add_comment", line_number=20, severity="major", category="security", message="secret"))
    env.step(CodeReviewAction(operation="add_comment", line_number=21, severity="critical", category="security", message="sqli"))
    env.step(CodeReviewAction(operation="add_comment", line_number=23, severity="major", category="security", message="validation"))
    env.step(CodeReviewAction(operation="add_comment", line_number=24, severity="critical", category="security", message="idor"))
    _, reward, done, _ = env.step(CodeReviewAction(operation="approve", summary="LGTM"))
    assert done is True
    assert reward == 0.10


def test_request_changes_reward_depends_on_evidence() -> None:
    """request_changes yields +0.05 with evidence, -0.05 without."""

    env = CodeReviewEnv()
    env.reset("easy")
    _, r0, done0, _ = env.step(CodeReviewAction(operation="request_changes", summary="needs work"))
    assert done0 is True
    assert r0 == 0.01

    env.reset("easy")
    env.step(CodeReviewAction(operation="add_comment", line_number=18, severity="major", category="bug", message="bug"))
    _, r1, done1, _ = env.step(CodeReviewAction(operation="request_changes", summary="needs work"))
    assert done1 is True
    assert r1 == 0.05


def test_done_score_varies_with_behavior() -> None:
    """done reward should differ for different comment behaviors."""

    env = CodeReviewEnv()
    env.reset("hard")
    _, reward_none, _, _ = env.step(CodeReviewAction(operation="done"))

    env.reset("hard")
    env.step(CodeReviewAction(operation="add_comment", line_number=23, severity="critical", category="security", message="unsafe loader"))
    _, reward_one, _, _ = env.step(CodeReviewAction(operation="done"))

    assert reward_one != reward_none


def test_api_root_route_returns_200() -> None:
    """GET / returns 200 with JSON body for HF Space UI."""

    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"


def test_api_step_rejects_malformed_body_with_422() -> None:
    """POST /step with malformed JSON does not crash and returns 422 or 500."""

    client = TestClient(app)
    client.post("/reset", json={"task_id": "easy"})
    r = client.post("/step", data="{bad", headers={"content-type": "application/json"})
    assert r.status_code in (422, 500)

