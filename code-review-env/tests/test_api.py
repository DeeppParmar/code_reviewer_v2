"""API tests for FastAPI server endpoints."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from server import app


@pytest.fixture()
def client() -> TestClient:
    """Create a test client for the FastAPI app."""

    return TestClient(app)


def test_post_reset_returns_200(client: TestClient) -> None:
    """POST /reset returns HTTP 200."""

    r = client.post("/reset", json={"task_id": "easy"})
    assert r.status_code == 200
    body = r.json()
    assert body["task_id"] == "easy"


def test_post_reset_invalid_task_id_returns_400_or_422(client: TestClient) -> None:
    """POST /reset with invalid task_id returns HTTP 422 or HTTP 400."""

    r = client.post("/reset", json={"task_id": "nope"})
    assert r.status_code in (400, 422)


def test_post_step_returns_200(client: TestClient) -> None:
    """POST /step returns HTTP 200."""

    client.post("/reset", json={"task_id": "easy"})
    r = client.post(
        "/step",
        json={"operation": "add_comment", "line_number": 2, "severity": "minor", "category": "style", "message": "nit"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "observation" in body and "reward" in body and "done" in body and "info" in body


def test_get_state_returns_200(client: TestClient) -> None:
    """GET /state returns HTTP 200."""

    r = client.get("/state")
    assert r.status_code == 200


def test_get_health_returns_200_ok(client: TestClient) -> None:
    """GET /health returns HTTP 200 with status ok."""

    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_server_does_not_crash_on_malformed_json(client: TestClient) -> None:
    """Malformed JSON body should not crash server."""

    r = client.post("/reset", data="{bad", headers={"content-type": "application/json"})
    assert r.status_code in (400, 422, 500)

