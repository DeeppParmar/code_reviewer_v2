"""Reward engine for CodeReviewEnv.

Implements non-sparse, shaped rewards according to the master spec.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from env.graders.grader_easy import grade as grade_easy
from env.graders.grader_hard import grade as grade_hard
from env.graders.grader_medium import grade as grade_medium
from env.models import CodeReviewAction, GroundTruthBug, ReviewComment


@dataclass(frozen=True)
class RewardOutcome:
    """Outcome details from reward computation."""

    reward: float
    reason: str
    correctly_identified_bug_line: Optional[int]
    is_false_positive: bool
    is_red_herring_flag: bool
    is_duplicate: bool
    final_score: Optional[float]


class RewardEngine:
    """Compute shaped rewards and final scores for a task episode."""

    def __init__(self, *, task_id: str, ground_truth: List[GroundTruthBug], max_steps: int) -> None:
        """Initialize the reward engine for a task."""

        self._task_id = task_id
        self._ground_truth = ground_truth
        self._max_steps = max_steps

    def _match_bug(self, line_number: int) -> Optional[GroundTruthBug]:
        """Find the closest ground-truth bug within +/-5 lines, preferring exact matches."""

        candidates: List[Tuple[int, GroundTruthBug]] = []
        for b in self._ground_truth:
            dist = abs(b.line_number - line_number)
            if dist <= 5:
                candidates.append((dist, b))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[0], x[1].line_number))
        return candidates[0][1]

    def _grade(self, comments: List[ReviewComment]) -> float:
        """Run the deterministic grader for this task."""

        if self._task_id == "easy":
            return grade_easy(comments, self._ground_truth)
        if self._task_id == "medium":
            return grade_medium(comments, self._ground_truth)
        if self._task_id == "hard":
            return grade_hard(comments, self._ground_truth)
        return 0.0

    def compute(
        self,
        action: CodeReviewAction,
        *,
        comments_so_far: List[ReviewComment],
        correctly_identified_bug_lines: set[int],
        step_number: int,
        steps_used_after_this: int,
    ) -> RewardOutcome:
        """Compute reward for an action.

        Args:
            action: Agent action.
            comments_so_far: Existing comments before applying this action.
            correctly_identified_bug_lines: Bug line numbers already credited.
            step_number: Current step number (1-indexed).
            steps_used_after_this: Step count used after applying this step (for efficiency bonus).

        Returns:
            RewardOutcome with reward and metadata.
        """

        if action.operation == "add_comment":
            if action.line_number is None:
                return RewardOutcome(
                    reward=-0.05,
                    reason="Invalid add_comment: missing line_number",
                    correctly_identified_bug_line=None,
                    is_false_positive=True,
                    is_red_herring_flag=False,
                    is_duplicate=False,
                    final_score=None,
                )

            matched = self._match_bug(action.line_number)
            if matched is None:
                return RewardOutcome(
                    reward=-0.10,
                    reason="False positive: no ground-truth bug near commented line",
                    correctly_identified_bug_line=None,
                    is_false_positive=True,
                    is_red_herring_flag=False,
                    is_duplicate=False,
                    final_score=None,
                )

            if matched.is_red_herring:
                return RewardOutcome(
                    reward=-0.20,
                    reason="Flagged red herring",
                    correctly_identified_bug_line=None,
                    is_false_positive=False,
                    is_red_herring_flag=True,
                    is_duplicate=False,
                    final_score=None,
                )

            if matched.line_number in correctly_identified_bug_lines:
                return RewardOutcome(
                    reward=-0.05,
                    reason="Duplicate comment on already-identified bug",
                    correctly_identified_bug_line=None,
                    is_false_positive=False,
                    is_red_herring_flag=False,
                    is_duplicate=True,
                    final_score=None,
                )

            base = 0.15
            sev_bonus = 0.05 if action.severity == matched.severity else 0.0
            cat_bonus = 0.05 if action.category == matched.category else 0.0
            semantic_penalty = 0.0

            # Semantic Understanding Check (The "Why" Metric)
            if matched.required_keywords and action.message:
                msg_lower = action.message.lower()
                has_keyword = any(kw.lower() in msg_lower for kw in matched.required_keywords)
                if not has_keyword:
                    semantic_penalty = -0.10

            reward = min(0.25, base + sev_bonus + cat_bonus) + semantic_penalty
            
            # If they failed the semantic check, we do NOT register this line as fully correctly identified.
            # We flag it internally so the agent still gets a partial shape reward but fails final grading.
            registered_line = None if semantic_penalty < 0 else matched.line_number

            return RewardOutcome(
                reward=reward,
                reason="Correct proximity but missed semantic 'why'" if semantic_penalty < 0 else "Correct bug proximity match",
                correctly_identified_bug_line=registered_line,
                is_false_positive=False,
                is_red_herring_flag=False,
                is_duplicate=False,
                final_score=None,
            )

        if action.operation == "approve":
            remaining_critical_or_major = [
                b
                for b in self._ground_truth
                if (not b.is_red_herring) and b.severity in {"critical", "major"} and b.line_number not in correctly_identified_bug_lines
            ]
            if remaining_critical_or_major:
                return RewardOutcome(
                    reward=-0.50,
                    reason="Approved while critical/major bugs remain unfound",
                    correctly_identified_bug_line=None,
                    is_false_positive=False,
                    is_red_herring_flag=False,
                    is_duplicate=False,
                    final_score=None,
                )
            return RewardOutcome(
                reward=0.10,
                reason="Approved with no critical/major bugs remaining",
                correctly_identified_bug_line=None,
                is_false_positive=False,
                is_red_herring_flag=False,
                is_duplicate=False,
                final_score=None,
            )

        if action.operation == "request_changes":
            if len(correctly_identified_bug_lines) > 0:
                return RewardOutcome(
                    reward=0.05,
                    reason="Requested changes with evidence",
                    correctly_identified_bug_line=None,
                    is_false_positive=False,
                    is_red_herring_flag=False,
                    is_duplicate=False,
                    final_score=None,
                )
            return RewardOutcome(
                reward=-0.05,
                reason="Requested changes without evidence",
                correctly_identified_bug_line=None,
                is_false_positive=False,
                is_red_herring_flag=False,
                is_duplicate=False,
                final_score=None,
            )

        if action.operation == "done":
            final_score = self._grade(comments_so_far)
            reward = float(final_score)
            if steps_used_after_this < int(0.6 * self._max_steps) and final_score > 0.8:
                reward += 0.10
            return RewardOutcome(
                reward=reward,
                reason="Final grading score",
                correctly_identified_bug_line=None,
                is_false_positive=False,
                is_red_herring_flag=False,
                is_duplicate=False,
                final_score=final_score,
            )

        return RewardOutcome(
            reward=-0.05,
            reason="Unknown operation",
            correctly_identified_bug_line=None,
            is_false_positive=True,
            is_red_herring_flag=False,
            is_duplicate=False,
            final_score=None,
        )

