"""Easy task definition.

Provides a simple Python data-processing utility with exactly 3 real bugs and
no red herrings, plus ground truth metadata with exact line numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from env.models import GroundTruthBug


@dataclass(frozen=True)
class TaskSpec:
    """Container for a task specification used by the environment."""

    task_id: str
    max_steps: int
    pr_title: str
    pr_description: str
    full_file: str
    code_diff: str
    ground_truth: List[GroundTruthBug]


def get_task() -> TaskSpec:
    """Return the easy task specification (buggy code + ground truth)."""

    full_file = "\n".join(
        [
            "from __future__ import annotations",
            "",
            "from dataclasses import dataclass",
            "from typing import Iterable, List, Optional",
            "",
            "",
            "@dataclass",
            "class Item:",
            "    value: int",
            "",
            "",
            "def summarize_adjacent_deltas(items: List[Optional[Item]]) -> List[int]:",
            '    """Compute deltas between adjacent item values.',
            "",
            "    Returns a list of differences: items[i+1].value - items[i].value.",
            "    \"\"\"",
            "    deltas: List[int] = []",
            "    for i in range(len(items)):",
            "        left = items[i]",
            "        right = items[i + 1]",
            "        if left.value < 0:",
            "            continue",
            "        delta = right.value - left.value",
            "        include = False",
            "        if include = delta > 0:",
            "            deltas.append(delta)",
            "    return deltas",
            "",
        ]
    )

    code_diff = "\n".join(
        [
            "--- a/utils.py",
            "+++ b/utils.py",
            "@@",
            "+def summarize_adjacent_deltas(items: List[Optional[Item]]) -> List[int]:",
            "+    deltas: List[int] = []",
            "+    for i in range(len(items)):",
            "+        left = items[i]",
            "+        right = items[i + 1]",
            "+        if left.value < 0:",
            "+            continue",
            "+        delta = right.value - left.value",
            "+        include = False",
            "+        if include = delta > 0:",
            "+            deltas.append(delta)",
            "+    return deltas",
        ]
    )

    ground_truth = [
        GroundTruthBug(
            line_number=18,
            severity="major",
            category="bug",
            description="Off-by-one: loop iterates full len(items) while accessing items[i+1], causing IndexError on last iteration.",
        ),
        GroundTruthBug(
            line_number=21,
            severity="major",
            category="bug",
            description="Missing null check: left can be None; accessing left.value crashes when None is present in the list.",
        ),
        GroundTruthBug(
            line_number=25,
            severity="minor",
            category="bug",
            description="Uses assignment '=' inside a conditional instead of '==', causing a syntax/logic error and making the condition invalid.",
        ),
    ]

    return TaskSpec(
        task_id="easy",
        max_steps=8,
        pr_title="Add utility to compute adjacent deltas",
        pr_description=(
            "This PR adds a small helper used by reporting code to compute per-step deltas "
            "from a list of Items. The function should be robust to missing entries."
        ),
        full_file=full_file,
        code_diff=code_diff,
        ground_truth=ground_truth,
    )

