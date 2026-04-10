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
    confidence_modifier: float = 0.0
    explanation_depth: Optional[str] = None


class RewardEngine:
    """Compute shaped rewards and final scores for a task episode."""

    def __init__(self, *, task_id: str, ground_truth: List[GroundTruthBug], max_steps: int) -> None:
        """Initialize the reward engine for a task."""

        self._task_id = task_id
        self._ground_truth = ground_truth
        self._max_steps = max_steps

    def _match_bug(self, line_number: int, filename: Optional[str] = None) -> Optional[GroundTruthBug]:
        """Find the closest ground-truth bug within +/-5 lines, preferring exact matches.

        Args:
            line_number: The line number to match against.
            filename: Optional filename for multi-file matching (Upgrade 4).
        """

        candidates: List[Tuple[int, GroundTruthBug]] = []
        for b in self._ground_truth:
            # Upgrade 4: If filename provided, only match bugs in that file
            if filename is not None and b.source_file is not None and b.source_file != filename:
                continue
            dist = abs(b.line_number - line_number)
            if dist <= 5:
                candidates.append((dist, b))
        if not candidates:
            # Upgrade 4: If filename was specified but no match, try all files (backward compatible)
            if filename is not None:
                return self._match_bug(line_number, filename=None)
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

    def _evaluate_explanation_tiers(self, bug: GroundTruthBug, message: str) -> Tuple[bool, float, str]:
        """Upgrade 2: Evaluate explanation quality against tiered keywords.

        Args:
            bug: The matched ground-truth bug.
            message: The agent's comment message.

        Returns:
            Tuple of (should_register, reward_modifier, explanation_depth).
        """
        if bug.explanation_tiers is None:
            # Fall back to existing required_keywords logic
            return self._evaluate_required_keywords(bug, message)

        msg_lower = message.lower()
        tiers = bug.explanation_tiers

        tier3_keywords = tiers.get("tier3", [])
        tier2_keywords = tiers.get("tier2", [])
        tier1_keywords = tiers.get("tier1", [])

        has_tier3 = any(kw.lower() in msg_lower for kw in tier3_keywords) if tier3_keywords else False
        has_tier2 = any(kw.lower() in msg_lower for kw in tier2_keywords) if tier2_keywords else False
        has_tier1 = any(kw.lower() in msg_lower for kw in tier1_keywords) if tier1_keywords else False

        if has_tier3:
            # Deep explanation — full credit + bonus
            return True, 0.05, "deep"
        elif has_tier2:
            # Technical explanation — full credit, no bonus
            return True, 0.0, "technical"
        elif has_tier1:
            # Shallow mention — registered but with penalty
            return True, -0.05, "shallow"
        else:
            # No match at all — not registered, penalty
            return False, -0.10, "missing"

    def _evaluate_required_keywords(self, bug: GroundTruthBug, message: str) -> Tuple[bool, float, str]:
        """Original required_keywords logic for backward compatibility.

        Returns:
            Tuple of (should_register, reward_modifier, explanation_depth).
        """
        if not bug.required_keywords or not message:
            return True, 0.0, "technical"

        msg_lower = message.lower()
        has_keyword = any(kw.lower() in msg_lower for kw in bug.required_keywords)
        if has_keyword:
            return True, 0.0, "technical"
        else:
            return False, -0.10, "missing"

    def _compute_confidence_modifier(
        self,
        confidence: Optional[int],
        is_correct: bool,
        is_false_positive: bool,
        is_red_herring: bool,
    ) -> float:
        """Upgrade 1: Compute calibration modifier based on confidence level.

        Args:
            confidence: Agent's confidence value (0-100) or None.
            is_correct: Whether the bug was correctly matched.
            is_false_positive: Whether this was a false positive.
            is_red_herring: Whether this hit a red herring.

        Returns:
            Modifier to add to the base reward.
        """
        if confidence is None:
            return 0.0

        if 80 <= confidence <= 100:
            if is_correct and not is_false_positive and not is_red_herring:
                return 0.05  # High confidence + correct → bonus
            elif is_false_positive:
                return -0.10  # High confidence + false positive → extra penalty
            elif is_red_herring:
                return -0.10  # High confidence + red herring → extra penalty
        elif 50 <= confidence <= 79:
            return 0.0  # Medium confidence → no modifier
        elif 0 <= confidence <= 49:
            if is_correct and not is_false_positive and not is_red_herring:
                return -0.02  # Low confidence + correct → should know when it knows

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

        # Upgrade 4: Handle inspect_file and inspect_lines actions
        if action.operation == "inspect_file":
            return RewardOutcome(
                reward=0.0,
                reason="Inspected file",
                correctly_identified_bug_line=None,
                is_false_positive=False,
                is_red_herring_flag=False,
                is_duplicate=False,
                final_score=None,
            )

        if action.operation == "inspect_lines":
            # Check if the inspected range contains a real bug line
            if action.start_line is not None and action.end_line is not None:
                for b in self._ground_truth:
                    if not b.is_red_herring and action.start_line <= b.line_number <= action.end_line:
                        if action.filename is None or b.source_file is None or action.filename == b.source_file:
                            return RewardOutcome(
                                reward=0.02,
                                reason="Inspected range contains a real bug",
                                correctly_identified_bug_line=None,
                                is_false_positive=False,
                                is_red_herring_flag=False,
                                is_duplicate=False,
                                final_score=None,
                            )
            return RewardOutcome(
                reward=0.0,
                reason="Inspected range contains no bugs",
                correctly_identified_bug_line=None,
                is_false_positive=False,
                is_red_herring_flag=False,
                is_duplicate=False,
                final_score=None,
            )

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

            matched = self._match_bug(action.line_number, filename=action.filename)
            if matched is None:
                # False positive
                conf_mod = self._compute_confidence_modifier(
                    action.confidence, is_correct=False,
                    is_false_positive=True, is_red_herring=False,
                )
                base_reward = -0.10 + conf_mod
                return RewardOutcome(
                    reward=base_reward,
                    reason="False positive: no ground-truth bug near commented line",
                    correctly_identified_bug_line=None,
                    is_false_positive=True,
                    is_red_herring_flag=False,
                    is_duplicate=False,
                    final_score=None,
                    confidence_modifier=conf_mod,
                )

            if matched.is_red_herring:
                conf_mod = self._compute_confidence_modifier(
                    action.confidence, is_correct=False,
                    is_false_positive=False, is_red_herring=True,
                )
                base_reward = -0.20 + conf_mod
                return RewardOutcome(
                    reward=base_reward,
                    reason="Flagged red herring",
                    correctly_identified_bug_line=None,
                    is_false_positive=False,
                    is_red_herring_flag=True,
                    is_duplicate=False,
                    final_score=None,
                    confidence_modifier=conf_mod,
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

            # Upgrade 2: Use tiered evaluation if explanation_tiers is present
            should_register, semantic_modifier, explanation_depth = self._evaluate_explanation_tiers(
                matched, action.message or ""
            )

            reward = min(0.25, base + sev_bonus + cat_bonus) + semantic_modifier

            registered_line = matched.line_number if should_register else None

            # Upgrade 1: Apply confidence modifier AFTER all existing logic
            is_correct = registered_line is not None
            conf_mod = self._compute_confidence_modifier(
                action.confidence, is_correct=is_correct,
                is_false_positive=False, is_red_herring=False,
            )
            reward += conf_mod

            return RewardOutcome(
                reward=reward,
                reason="Correct proximity but missed semantic 'why'" if not should_register else "Correct bug proximity match",
                correctly_identified_bug_line=registered_line,
                is_false_positive=False,
                is_red_herring_flag=False,
                is_duplicate=False,
                final_score=None,
                confidence_modifier=conf_mod,
                explanation_depth=explanation_depth,
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
