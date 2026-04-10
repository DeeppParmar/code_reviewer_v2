"""Medium task grader."""

from __future__ import annotations

from typing import List

from env.graders.base_grader import compute_weighted_f1
from env.models import GroundTruthBug, ReviewComment


def grade(comments: List[ReviewComment], ground_truth: List[GroundTruthBug]) -> float:
    """Grade the medium task based on agent comments.

    Matching rules mirror the easy grader and remain deterministic.

    Args:
        comments: All agent comments made in the episode.
        ground_truth: Ground-truth bugs for the task.

    Returns:
        Deterministic score in [0.0, 1.0].
    """

    found: List[GroundTruthBug] = []
    for bug in ground_truth:
        if bug.is_red_herring:
            continue
        for c in comments:
            if abs(c.line_number - bug.line_number) <= 5 and c.severity == bug.severity and c.category == bug.category:
                if bug.required_keywords and c.message:
                    msg_lower = c.message.lower()
                    has_keyword = any(kw.lower() in msg_lower for kw in bug.required_keywords)
                    if not has_keyword:
                        continue
                found.append(bug)
                break
    return compute_weighted_f1(found_bugs=found, all_bugs=ground_truth, total_comments=len(comments))

