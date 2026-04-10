"""State manager for CodeReviewEnv episodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from env.models import CodeReviewAction, GroundTruthBug, ReviewComment


@dataclass
class StateManager:
    """Track the full episode state for a single task run."""

    task_id: str
    step_number: int = 1
    comments: List[ReviewComment] = field(default_factory=list)
    correctly_identified_bug_lines: Set[int] = field(default_factory=set)
    false_positives: int = 0
    red_herring_flags: int = 0
    cumulative_reward: float = 0.0
    done: bool = False
    last_error: Optional[str] = None
    # Upgrade 1: Calibration tracking
    calibration_events: List[dict] = field(default_factory=list)
    # Upgrade 2: Explanation depth tracking per found bug
    explanation_depths: Dict[int, str] = field(default_factory=dict)
    # Upgrade 3: Injection resistance tracking
    injection_resistance: Optional[bool] = None

    def record_action(
        self,
        action: CodeReviewAction,
        reward: float,
        *,
        new_comment: Optional[ReviewComment] = None,
        correctly_identified_bug_line: Optional[int] = None,
        is_false_positive: bool = False,
        is_red_herring_flag: bool = False,
        error: Optional[str] = None,
        confidence_modifier: float = 0.0,
        explanation_depth: Optional[str] = None,
    ) -> None:
        """Record an action outcome into state.

        Args:
            action: The action applied.
            reward: Scalar reward returned for the step.
            new_comment: If action added a comment, the created ReviewComment.
            correctly_identified_bug_line: Bug line number credited as found (if any).
            is_false_positive: Whether the action counted as a false positive.
            is_red_herring_flag: Whether the action flagged a red herring.
            error: Error message (if any).
            confidence_modifier: Upgrade 1 — calibration modifier applied.
            explanation_depth: Upgrade 2 — depth of explanation for this bug.
        """

        if new_comment is not None:
            self.comments.append(new_comment)

        if correctly_identified_bug_line is not None:
            self.correctly_identified_bug_lines.add(correctly_identified_bug_line)
            # Track explanation depth for this bug
            if explanation_depth is not None:
                self.explanation_depths[correctly_identified_bug_line] = explanation_depth

        if is_false_positive:
            self.false_positives += 1

        if is_red_herring_flag:
            self.red_herring_flags += 1

        # Upgrade 1: Record calibration event for add_comment actions
        if action.operation == "add_comment":
            was_correct = (
                correctly_identified_bug_line is not None
                and not is_false_positive
                and not is_red_herring_flag
            )
            self.calibration_events.append({
                "step": self.step_number,
                "confidence": action.confidence if hasattr(action, "confidence") else None,
                "was_correct": was_correct,
                "modifier_applied": confidence_modifier,
            })

        self.cumulative_reward += reward
        self.last_error = error

        self.step_number += 1

        if action.operation in {"done", "approve", "request_changes"}:
            self.done = True

    def get_correctly_found_bugs(self, ground_truth: List[GroundTruthBug]) -> List[GroundTruthBug]:
        """Return the list of ground-truth bugs correctly found so far.

        Args:
            ground_truth: All bugs for the current task.

        Returns:
            Subset of ground_truth whose line_number has been credited as found.
        """

        by_line: Dict[int, GroundTruthBug] = {b.line_number: b for b in ground_truth}
        found: List[GroundTruthBug] = []
        for line in sorted(self.correctly_identified_bug_lines):
            bug = by_line.get(line)
            if bug is not None and not bug.is_red_herring:
                found.append(bug)
        return found

    def get_false_positive_count(self) -> int:
        """Return the number of false positives recorded so far."""

        return self.false_positives + self.red_herring_flags

    def compute_injection_resistance(self, ground_truth: List[GroundTruthBug], injected_lines: List[int]) -> None:
        """Upgrade 3: Determine if the agent resisted adversarial injections.

        Args:
            ground_truth: All ground truth bugs.
            injected_lines: Line numbers of real bugs that have adversarial comments above them.
        """
        if not injected_lines:
            self.injection_resistance = None
            return

        # Check if the agent found the real bugs on injected lines
        found_injected = all(line in self.correctly_identified_bug_lines for line in injected_lines)
        self.injection_resistance = found_injected

    def get_explanation_depth_distribution(self) -> Dict[str, int]:
        """Upgrade 2: Return distribution of explanation depths."""
        dist = {"deep": 0, "technical": 0, "shallow": 0, "missing": 0}
        for depth in self.explanation_depths.values():
            if depth in dist:
                dist[depth] += 1
        return dist

    def to_dict(self) -> dict:
        """Serialize current state to a plain dictionary for the /state endpoint."""

        return {
            "task_id": self.task_id,
            "step_number": self.step_number,
            "comments": [c.model_dump() for c in self.comments],
            "running_score": max(0.001, min(0.999, self.cumulative_reward)),
            "bugs_found": len(self.correctly_identified_bug_lines),
            "false_positives": self.get_false_positive_count(),
            "red_herring_flags": self.red_herring_flags,
            "done": self.done,
            "last_error": self.last_error,
            "calibration_events": self.calibration_events,
            "explanation_depth_distribution": self.get_explanation_depth_distribution(),
            "injection_resistance": self.injection_resistance,
        }
