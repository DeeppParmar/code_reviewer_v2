"""Shared grading utilities for code-review tasks.

Implements deterministic F1 and weighted F1 scoring.
"""

from __future__ import annotations

from typing import Dict, List

from env.models import GroundTruthBug


def compute_f1(correctly_identified: int, total_comments: int, total_real_bugs: int) -> float:
    """Compute standard F1 score, rounded to 4 decimals.

    Args:
        correctly_identified: Number of real bugs correctly identified.
        total_comments: Total number of comments made by the agent.
        total_real_bugs: Total number of real bugs in the task (excluding red herrings).

    Returns:
        F1 score in [0.0, 1.0], rounded to 4 decimals.
    """

    precision = correctly_identified / total_comments if total_comments > 0 else 0.0
    recall = correctly_identified / total_real_bugs if total_real_bugs > 0 else 0.0
    if precision + recall == 0.0:
        return 0.001
    f1 = 2.0 * precision * recall / (precision + recall)
    return max(0.001, min(0.999, round(f1, 4)))


def _severity_weight(severity: str) -> float:
    """Return the weight for a severity label."""

    weights: Dict[str, float] = {"critical": 3.0, "major": 2.0, "minor": 1.0, "nit": 0.5}
    return weights.get(severity, 1.0)


def compute_weighted_f1(found_bugs: List[GroundTruthBug], all_bugs: List[GroundTruthBug], total_comments: int) -> float:
    """Compute weighted F1 where bug severities have different importance.

    Severity weights:
      - critical: 3
      - major: 2
      - minor: 1
      - nit: 0.5

    Args:
        found_bugs: Ground-truth bug objects that the agent correctly identified.
        all_bugs: All ground-truth bugs for the task (may include red herrings).
        total_comments: Total number of comments made by the agent.

    Returns:
        Weighted F1 score in [0.0, 1.0].
    """

    real_bugs = [b for b in all_bugs if not b.is_red_herring]
    total_real_weight = sum(_severity_weight(b.severity) for b in real_bugs)
    found_real = [b for b in found_bugs if not b.is_red_herring]
    found_weight = sum(_severity_weight(b.severity) for b in found_real)

    weighted_precision = found_weight / total_comments if total_comments > 0 else 0.0
    weighted_recall = found_weight / total_real_weight if total_real_weight > 0 else 0.0

    if weighted_precision + weighted_recall == 0.0:
        return 0.001

    score = 2.0 * weighted_precision * weighted_recall / (weighted_precision + weighted_recall)
    return max(0.001, min(0.999, round(score, 4)))

