"""Shared grading utilities for code-review tasks.

Implements deterministic F1 and weighted F1 scoring.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from env.models import GroundTruthBug, ReviewComment


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


def compute_weighted_f1(
    found_bugs: List[GroundTruthBug],
    all_bugs: List[GroundTruthBug],
    total_comments: int,
    comments: Optional[List[ReviewComment]] = None,
    matched_indices: Optional[set] = None,
) -> float:
    """Compute weighted F1 where bug severities have different importance.

    Uses proper weighted precision: weighted_tp / (weighted_tp + weighted_fp)
    where FPs are also weighted by the severity the agent assigned to them.
    This prevents precision from exceeding 1.0 when high-severity bugs are found.

    Severity weights:
      - critical: 3
      - major: 2
      - minor: 1
      - nit: 0.5

    Args:
        found_bugs: Ground-truth bug objects that the agent correctly identified.
        all_bugs: All ground-truth bugs for the task (may include red herrings).
        total_comments: Total number of comments made by the agent.
        comments: Optional full list of agent comments for computing weighted FP penalty.
        matched_indices: Set of comment indices that were matched as true positives.
            If provided, any comment NOT in this set is a false positive.

    Returns:
        Weighted F1 score in [0.0, 1.0].
    """

    real_bugs = [b for b in all_bugs if not b.is_red_herring]
    total_real_weight = sum(_severity_weight(b.severity) for b in real_bugs)
    found_real = [b for b in found_bugs if not b.is_red_herring]
    found_weight = sum(_severity_weight(b.severity) for b in found_real)

    # Compute weighted false positive penalty.
    # Each FP comment is weighted by its severity to properly penalize precision.
    fp_count = max(0, total_comments - len(found_real))

    if comments is not None and fp_count > 0:
        fp_weight = 0.0
        for idx, c in enumerate(comments):
            # A comment is a true positive ONLY if its index was in matched_indices
            if matched_indices is not None:
                is_tp = idx in matched_indices
            else:
                # Legacy fallback: proximity-based (should not be used)
                found_lines = {b.line_number for b in found_real}
                is_tp = any(abs(c.line_number - bl) <= 5 for bl in found_lines)
            if not is_tp:
                fp_weight += _severity_weight(c.severity)
    else:
        # Fallback: assign each FP a default weight of 2.0 (major severity)
        fp_weight = fp_count * 2.0

    # Missed bugs weight (false negatives)
    missed_weight = max(0.0, total_real_weight - found_weight)

    # Weighted precision: tp_weight / (tp_weight + fp_weight)
    precision_denom = found_weight + fp_weight
    weighted_precision = found_weight / precision_denom if precision_denom > 0 else 0.0

    # Weighted recall: tp_weight / (tp_weight + fn_weight)
    weighted_recall = found_weight / total_real_weight if total_real_weight > 0 else 0.0

    if weighted_precision + weighted_recall == 0.0:
        return 0.001

    score = 2.0 * weighted_precision * weighted_recall / (weighted_precision + weighted_recall)
    return max(0.001, min(0.999, round(score, 4)))


def compute_calibration_score(calibration_events: List[dict]) -> Optional[float]:
    """Upgrade 1: Compute a calibration score from calibration events.

    For each event where confidence is not None:
      - correct + high confidence (80-100): +1 point
      - correct + low confidence (0-49): +0.5 point
      - wrong + high confidence (80-100): -1 point
      - wrong + low confidence (0-49): 0 points
      - mid-range confidence (50-79): 0 points regardless

    calibration_score = (sum_of_points + total_events) / (2 * total_events)
    Clamped to (0.001, 0.999).

    If no confidence values were provided: returns None.

    Args:
        calibration_events: List of calibration event dicts from state manager.

    Returns:
        Calibration score or None if no confidence values were provided.
    """
    events_with_confidence = [
        e for e in calibration_events if e.get("confidence") is not None
    ]

    if not events_with_confidence:
        return None

    total_events = len(events_with_confidence)
    total_points = 0.0

    for event in events_with_confidence:
        confidence = event["confidence"]
        was_correct = event.get("was_correct", False)

        if 80 <= confidence <= 100:
            if was_correct:
                total_points += 1.0
            else:
                total_points -= 1.0
        elif 0 <= confidence <= 49:
            if was_correct:
                total_points += 0.5
            # wrong + low confidence: 0 points
        # 50-79: 0 points regardless

    raw_score = (total_points + total_events) / (2.0 * total_events)
    return max(0.001, min(0.999, round(raw_score, 4)))
