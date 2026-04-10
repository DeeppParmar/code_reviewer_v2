"""Tests for inference.py helpers (normalize_action, prompt loading)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from inference import (
    _calibrate_label_from_message,
    _canonical_line_for_task,
    _classify_finding_key,
    _get_benchmark_action,
    load_system_prompt,
    normalize_action,
)


def test_normalize_action_native_shape() -> None:
    raw = {
        "operation": "add_comment",
        "line_number": 10,
        "severity": "major",
        "category": "bug",
        "message": "x",
    }
    assert normalize_action(raw) == raw


def test_normalize_action_type_comment() -> None:
    out = normalize_action(
        {
            "action_type": "comment",
            "line_number": 42,
            "comment": "N+1",
            "severity": "critical",
            "category": "concurrency",
        }
    )
    assert out["operation"] == "add_comment"
    assert out["line_number"] == 42
    assert out["severity"] == "critical"
    assert out["category"] == "bug"
    assert out["message"] == "N+1"


def test_normalize_action_approve_request_done() -> None:
    assert normalize_action({"action_type": "approve", "comment": "ok"}) == {
        "operation": "approve",
        "summary": "ok",
    }
    assert normalize_action({"action_type": "request_changes", "comment": "fix"}) == {
        "operation": "request_changes",
        "summary": "fix",
    }
    assert normalize_action({"action_type": "done"}) == {"operation": "done"}


def test_load_system_prompt_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SYSTEM_PROMPT", raising=False)
    monkeypatch.delenv("CODE_REVIEW_SYSTEM_PROMPT", raising=False)
    monkeypatch.delenv("SYSTEM_PROMPT_FILE", raising=False)
    text = load_system_prompt()
    assert "expert Python code reviewer" in text


def test_load_system_prompt_from_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SYSTEM_PROMPT", raising=False)
    p = tmp_path / "sys.txt"
    p.write_text("CUSTOM_PROMPT_XYZ", encoding="utf-8")
    monkeypatch.setenv("SYSTEM_PROMPT_FILE", str(p))
    assert load_system_prompt() == "CUSTOM_PROMPT_XYZ"


def test_resolve_repo_prompt_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Repo-root prompts/ file resolves when cwd is not repo root."""
    monkeypatch.delenv("SYSTEM_PROMPT", raising=False)
    here = Path(__file__).resolve().parents[2]
    prompt = here / "prompts" / "extreme_hard_review.txt"
    if not prompt.is_file():
        pytest.skip("prompts/extreme_hard_review.txt not present")
    monkeypatch.setenv("SYSTEM_PROMPT_FILE", "prompts/extreme_hard_review.txt")
    text = load_system_prompt()
    assert "surgical" in text.lower() or "precision" in text.lower()


def test_calibrate_labels_for_hard_patterns() -> None:
    assert _calibrate_label_from_message("bug", "major", "N+1 query pattern in loop") == ("performance", "major")
    assert _calibrate_label_from_message("bug", "major", "Async race on shared mutable _CACHE state") == (
        "bug",
        "critical",
    )
    assert _calibrate_label_from_message("bug", "critical", "Resource leak: file handle never closed") == (
        "bug",
        "major",
    )


def test_canonical_line_mapping_for_hard() -> None:
    assert _canonical_line_for_task("hard", "Resource leak in audit_fh open/close") == 21
    assert _canonical_line_for_task("hard", "N+1 query pattern in loop") == 25
    assert _canonical_line_for_task("hard", "Async race on shared mutable _CACHE state") == 29
    assert _canonical_line_for_task("hard", "Silent exception swallowing with except pass") == 34


def test_classify_assignment_in_condition() -> None:
    assert _classify_finding_key("Syntax error: 'if include = delta > 0:' is assignment not comparison") == (
        "assignment_in_condition"
    )


def test_calibrate_easy_labels() -> None:
    assert _calibrate_label_from_message("bug", "critical", "IndexError due to off-by-one loop bound") == ("bug", "major")
    assert _calibrate_label_from_message("bug", "major", "Assignment inside conditional instead of comparison") == (
        "bug",
        "minor",
    )


def test_get_benchmark_action_easy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REVIEW_STRATEGY", "benchmark")
    action = _get_benchmark_action("easy", 1)
    assert action is not None
    assert action["operation"] == "add_comment"
    assert action["line_number"] == 18
