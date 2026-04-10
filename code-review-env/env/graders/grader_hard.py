"""Hard task grader (includes red herring)."""

from __future__ import annotations

from typing import List

from env.graders.base_grader import compute_weighted_f1
from env.models import GroundTruthBug, ReviewComment


def grade(comments: List[ReviewComment], ground_truth: List[GroundTruthBug]) -> float:
    """Grade the hard task based on agent comments.

    A bug is counted as correctly identified if the agent:
      - placed a comment within +/- 5 lines of the bug line, AND
      - matched severity and category exactly.

    Red herrings are not counted as "real bugs" for recall, but are still subject
    to false-positive pressure via the total_comments precision term.

    Args:
        comments: All agent comments made in the episode.
        ground_truth: Ground-truth bugs for the task, including a red herring.

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

