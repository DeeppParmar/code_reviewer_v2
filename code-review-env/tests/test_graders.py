"""Tests for grader correctness and determinism."""

from __future__ import annotations

from env.graders.grader_easy import grade as grade_easy
from env.graders.grader_hard import grade as grade_hard
from env.models import GroundTruthBug, ReviewComment


def test_grader_returns_zero_when_no_bugs_found() -> None:
    """No comments yields 0.0 score."""

    gt = [
        GroundTruthBug(line_number=10, severity="major", category="bug", description="x"),
        GroundTruthBug(line_number=20, severity="critical", category="security", description="y"),
    ]
    assert grade_easy([], gt) == 0.001


def test_grader_returns_one_when_all_bugs_found_with_correct_labels() -> None:
    """Perfect identification yields 1.0."""

    gt = [
        GroundTruthBug(line_number=10, severity="major", category="bug", description="x"),
        GroundTruthBug(line_number=20, severity="critical", category="security", description="y"),
    ]
    comments = [
        ReviewComment(line_number=10, severity="major", category="bug", message="x", step_added=1),
        ReviewComment(line_number=20, severity="critical", category="security", message="y", step_added=2),
    ]
    assert grade_easy(comments, gt) == 0.999


def test_grader_partial_is_strictly_between_zero_and_one() -> None:
    """Partial completion yields a score in (0.0, 1.0)."""

    gt = [
        GroundTruthBug(line_number=10, severity="major", category="bug", description="x"),
        GroundTruthBug(line_number=20, severity="critical", category="security", description="y"),
    ]
    comments = [ReviewComment(line_number=10, severity="major", category="bug", message="x", step_added=1)]
    score = grade_easy(comments, gt)
    assert 0.0 < score < 1.0


def test_grader_is_deterministic_across_multiple_calls() -> None:
    """Same inputs yield identical outputs across 5 calls."""

    gt = [
        GroundTruthBug(line_number=10, severity="major", category="bug", description="x"),
        GroundTruthBug(line_number=20, severity="critical", category="security", description="y"),
    ]
    comments = [ReviewComment(line_number=10, severity="major", category="bug", message="x", step_added=1)]
    results = [grade_easy(comments, gt) for _ in range(5)]
    assert all(r == results[0] for r in results)


def test_weighted_f1_rewards_critical_more_than_minor() -> None:
    """Finding critical bug should score higher than finding minor bug with same #comments."""

    gt = [
        GroundTruthBug(line_number=10, severity="minor", category="bug", description="minor"),
        GroundTruthBug(line_number=20, severity="critical", category="bug", description="critical"),
    ]
    minor_comment = [ReviewComment(line_number=10, severity="minor", category="bug", message="m", step_added=1)]
    critical_comment = [ReviewComment(line_number=20, severity="critical", category="bug", message="c", step_added=1)]
    assert grade_easy(critical_comment, gt) > grade_easy(minor_comment, gt)


def test_hard_grader_ignores_red_herring_as_real_bug() -> None:
    """Red herring should not improve recall as a real bug."""

    gt = [
        GroundTruthBug(line_number=10, severity="major", category="bug", description="real"),
        GroundTruthBug(line_number=12, severity="nit", category="style", description="trap", is_red_herring=True),
    ]
    trap_only = [ReviewComment(line_number=12, severity="nit", category="style", message="trap", step_added=1)]
    assert grade_hard(trap_only, gt) == 0.001

