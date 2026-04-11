"""Hard task grader (includes red herring + multi-file bugs)."""

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

    Supports multi-file bugs: bugs from different files are matched independently
    based on line number proximity (Upgrade 4).

    Args:
        comments: All agent comments made in the episode.
        ground_truth: Ground-truth bugs for the task, including a red herring.

    Returns:
        Deterministic score in [0.0, 1.0].
    """

    found: List[GroundTruthBug] = []
    used_indices = set()
    for bug in ground_truth:
        if bug.is_red_herring:
            continue
        best_dist = 999
        best_idx = -1
        for idx, c in enumerate(comments):
            if idx in used_indices:
                continue
            dist = abs(c.line_number - bug.line_number)
            if dist <= 5 and c.severity == bug.severity and c.category == bug.category:
                # Upgrade 2: Use explanation_tiers if available, else fall back to required_keywords
                if bug.explanation_tiers:
                    msg_lower = c.message.lower() if c.message else ""
                    tiers = bug.explanation_tiers
                    tier3_kws = tiers.get("tier3", [])
                    tier2_kws = tiers.get("tier2", [])
                    tier1_kws = tiers.get("tier1", [])
                    has_any = (
                        any(kw.lower() in msg_lower for kw in tier3_kws) or
                        any(kw.lower() in msg_lower for kw in tier2_kws) or
                        any(kw.lower() in msg_lower for kw in tier1_kws)
                    )
                    if not has_any:
                        continue
                elif bug.required_keywords and c.message:
                    msg_lower = c.message.lower()
                    has_keyword = any(kw.lower() in msg_lower for kw in bug.required_keywords)
                    if not has_keyword:
                        continue
                if dist < best_dist:
                    best_dist = dist
                    best_idx = idx

        if best_idx != -1:
            used_indices.add(best_idx)
            found.append(bug)
    return compute_weighted_f1(found_bugs=found, all_bugs=ground_truth, total_comments=len(comments), comments=comments, matched_indices=used_indices)
