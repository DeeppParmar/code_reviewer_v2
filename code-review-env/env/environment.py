"""Core environment implementation for Code Review OpenEnv."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from env.models import CodeReviewAction, CodeReviewObservation, ReviewComment
from env.reward_engine import RewardEngine
from env.state_manager import StateManager
from env.tasks.task_easy import get_task as get_easy
from env.tasks.task_hard import get_task as get_hard
from env.tasks.task_medium import get_task as get_medium


class CodeReviewEnv:
    """Gym-like environment for evaluating code-review agents."""

    def __init__(self) -> None:
        """Initialize environment with no active episode."""

        self._task_id: str | None = None
        self._max_steps: int = 0
        self._pr_title: str = ""
        self._pr_description: str = ""
        self._full_file: str = ""
        self._code_diff: str = ""
        self._ground_truth = []
        self._state: StateManager | None = None
        self._reward_engine: RewardEngine | None = None
        # Multi-file repository support
        self._repository_files: Optional[Dict[str, str]] = None
        self._available_files: Optional[List[str]] = None

    def reset(self, task_id: str) -> CodeReviewObservation:
        """Reset the environment to a fresh episode for the given task.

        Args:
            task_id: One of "easy", "medium", "hard".

        Returns:
            Initial observation with empty existing_comments.
        """

        if task_id == "easy":
            task = get_easy()
        elif task_id == "medium":
            task = get_medium()
        elif task_id == "hard":
            task = get_hard()
        else:
            raise ValueError(f"Unknown task_id: {task_id}")

        self._task_id = task.task_id
        self._max_steps = task.max_steps
        self._pr_title = task.pr_title
        self._pr_description = task.pr_description
        self._full_file = task.full_file
        self._code_diff = task.code_diff
        self._ground_truth = task.ground_truth

        # Store repository files if available
        self._repository_files = getattr(task, 'repository_files', None)
        self._available_files = getattr(task, 'available_files', None)

        self._state = StateManager(task_id=task.task_id)
        self._reward_engine = RewardEngine(task_id=task.task_id, ground_truth=task.ground_truth, max_steps=task.max_steps)

        return CodeReviewObservation(
            task_id=task.task_id,
            language="python",
            pr_title=self._pr_title,
            pr_description=self._pr_description,
            code_diff=self._code_diff,
            full_file=self._full_file,
            existing_comments=[],
            step_number=1,
            max_steps=self._max_steps,
            review_status="pending",
            repository_files=self._repository_files,
            available_files=self._available_files,
        )

    def step(self, action: CodeReviewAction) -> Tuple[CodeReviewObservation, float, bool, dict]:
        """Apply an action and advance the environment by one step.

        Args:
            action: CodeReviewAction describing the agent's operation.

        Returns:
            Tuple of (updated_observation, reward, done, info).
        """

        if self._state is None or self._reward_engine is None or self._task_id is None:
            raise RuntimeError("Environment must be reset() before step().")

        error: str | None = None
        reward: float
        new_comment: ReviewComment | None = None

        # Handle inspect_file action
        if action.operation == "inspect_file":
            if self._repository_files and action.filename and action.filename in self._repository_files:
                outcome = self._reward_engine.compute(
                    action,
                    comments_so_far=self._state.comments,
                    correctly_identified_bug_lines=self._state.correctly_identified_bug_lines,
                    step_number=self._state.step_number,
                    steps_used_after_this=self._state.step_number,
                )
                reward = outcome.reward
                self._state.record_action(action, reward, error=None)
            else:
                reward = 0.0
                error = f"File not found: {action.filename}"
                self._state.record_action(action, reward, error=error)

        # Handle inspect_lines action
        elif action.operation == "inspect_lines":
            if action.start_line is not None and action.end_line is not None:
                if action.end_line - action.start_line > 40:
                    reward = 0.0
                    error = "inspect_lines max range is 40 lines"
                    self._state.record_action(action, reward, error=error)
                elif self._repository_files and action.filename and action.filename in self._repository_files:
                    outcome = self._reward_engine.compute(
                        action,
                        comments_so_far=self._state.comments,
                        correctly_identified_bug_lines=self._state.correctly_identified_bug_lines,
                        step_number=self._state.step_number,
                        steps_used_after_this=self._state.step_number,
                    )
                    reward = outcome.reward
                    self._state.record_action(action, reward, error=None)
                else:
                    reward = 0.0
                    error = f"File not found: {action.filename}"
                    self._state.record_action(action, reward, error=error)
            else:
                reward = 0.0
                error = "inspect_lines requires start_line and end_line"
                self._state.record_action(action, reward, error=error)

        elif action.operation == "add_comment":
            if action.line_number is None:
                outcome = self._reward_engine.compute(
                    action,
                    comments_so_far=self._state.comments,
                    correctly_identified_bug_lines=self._state.correctly_identified_bug_lines,
                    step_number=self._state.step_number,
                    steps_used_after_this=self._state.step_number,
                )
                reward = outcome.reward
                error = "Missing line_number for add_comment"
                self._state.record_action(
                    action,
                    reward,
                    new_comment=None,
                    correctly_identified_bug_line=None,
                    is_false_positive=True,
                    is_red_herring_flag=False,
                    error=error,
                    confidence_modifier=outcome.confidence_modifier,
                )
            else:
                new_comment = ReviewComment(
                    line_number=action.line_number,
                    severity=action.severity or "minor",
                    category=action.category or "bug",
                    message=action.message or "Issue detected",
                    step_added=self._state.step_number,
                )
                outcome = self._reward_engine.compute(
                    action,
                    comments_so_far=self._state.comments + [new_comment],
                    correctly_identified_bug_lines=self._state.correctly_identified_bug_lines,
                    step_number=self._state.step_number,
                    steps_used_after_this=self._state.step_number,
                )
                reward = outcome.reward
                self._state.record_action(
                    action,
                    reward,
                    new_comment=new_comment,
                    correctly_identified_bug_line=outcome.correctly_identified_bug_line,
                    is_false_positive=outcome.is_false_positive,
                    is_red_herring_flag=outcome.is_red_herring_flag,
                    error=None,
                    confidence_modifier=outcome.confidence_modifier,
                    explanation_depth=outcome.explanation_depth,
                )
        else:
            outcome = self._reward_engine.compute(
                action,
                comments_so_far=self._state.comments,
                correctly_identified_bug_lines=self._state.correctly_identified_bug_lines,
                step_number=self._state.step_number,
                steps_used_after_this=self._state.step_number,
            )
            reward = outcome.reward
            self._state.record_action(action, reward, error=None)

        done = False
        if action.operation in {"done", "approve", "request_changes"}:
            done = True
        if self._state.step_number > self._max_steps:
            done = True
            if action.operation != "done":
                self._state.cumulative_reward += -0.20

        # On terminal actions, replace cumulative_reward with the final F1
        # grader score. The per-step shaped rewards guided the agent during
        # the episode, but the final reported score must be the deterministic
        # F1 result — NOT the sum of shaped rewards + F1.
        if done and action.operation in {"done", "approve", "request_changes"}:
            final_f1 = outcome.final_score if hasattr(outcome, "final_score") and outcome.final_score is not None else None
            if final_f1 is not None:
                # Replace, don't add — this is the fix for the 0.999 ceiling bug.
                self._state.cumulative_reward = final_f1
            else:
                # approve/request_changes or done without final_score — run grader.
                final_f1 = self._reward_engine._grade(self._state.comments)
                self._state.cumulative_reward = final_f1

        # Compute injection resistance at episode end for hard task
        if done and self._task_id == "hard":
            # The injected lines are the real bug lines that have adversarial comments above them
            # ECB bug (line 35) and race condition bug (line 47)
            injected_lines = [35, 47]
            self._state.compute_injection_resistance(self._ground_truth, injected_lines)

        # Clamp cumulative score to (0.0, 1.0) per OpenEnv strictly between bounds spec.
        clamped_score = max(0.001, min(0.999, self._state.cumulative_reward))
        info = {
            "bugs_found": len(self._state.correctly_identified_bug_lines),
            "false_positives": self._state.get_false_positive_count(),
            "current_score": clamped_score,
            "error": error,
        }

        obs = CodeReviewObservation(
            task_id=self._task_id,
            language="python",
            pr_title=self._pr_title,
            pr_description=self._pr_description,
            code_diff=self._code_diff,
            full_file=self._full_file,
            existing_comments=list(self._state.comments),
            step_number=max(1, self._state.step_number),
            max_steps=self._max_steps,
            review_status="submitted" if done else "in_review",
            repository_files=self._repository_files,
            available_files=self._available_files,
        )
        return obs, float(round(min(max(reward, 0.01), 0.99), 3)), bool(done), info

    def state(self) -> dict:
        """Return full current state as a plain dict."""

        if self._state is None:
            return {"task_id": None, "step_number": 0, "comments": [], "running_score": 0.01, "bugs_found": 0, "false_positives": 0}
        return self._state.to_dict()
