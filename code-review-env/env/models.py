"""Pydantic models for the Code Review OpenEnv environment.

These models define the observation, action, reward, and ground-truth bug schema
used across the environment, server API, and inference baseline.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ReviewComment(BaseModel):
    """A single review comment placed by the agent on a specific line."""

    model_config = ConfigDict(extra="forbid")

    line_number: int = Field(..., ge=1)
    severity: Literal["critical", "major", "minor", "nit"]
    category: Literal["bug", "security", "performance", "style"]
    message: str = Field(..., min_length=1)
    step_added: int = Field(..., ge=1)


class CodeReviewObservation(BaseModel):
    """Observation returned to the agent at each step."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(..., min_length=1)
    language: str = Field(..., min_length=1)
    pr_title: str = Field(..., min_length=1)
    pr_description: str = Field(..., min_length=1)
    code_diff: str
    full_file: str
    existing_comments: List[ReviewComment]
    step_number: int = Field(..., ge=1)
    max_steps: int = Field(..., ge=1)
    review_status: Literal["pending", "in_review", "submitted"]


class CodeReviewAction(BaseModel):
    """Action sent by the agent to the environment."""

    model_config = ConfigDict(extra="forbid")

    operation: Literal["add_comment", "approve", "request_changes", "done"]
    line_number: Optional[int] = Field(default=None, ge=1)
    severity: Optional[Literal["critical", "major", "minor", "nit"]] = None
    category: Optional[Literal["bug", "security", "performance", "style"]] = None
    message: Optional[str] = Field(default=None, min_length=1)
    summary: Optional[str] = Field(default=None, min_length=1)


class CodeReviewReward(BaseModel):
    """Reward breakdown returned by reward engine and recorded in state."""

    model_config = ConfigDict(extra="forbid")

    score: float
    reason: str = Field(..., min_length=1)
    cumulative_score: float
    bugs_found_so_far: int = Field(..., ge=0)
    false_positives_so_far: int = Field(..., ge=0)


class GroundTruthBug(BaseModel):
    """Ground-truth bug metadata used for rewards and grading."""

    model_config = ConfigDict(extra="forbid")

    line_number: int = Field(..., ge=1)
    severity: Literal["critical", "major", "minor", "nit"]
    category: Literal["bug", "security", "performance", "style"]
    description: str = Field(..., min_length=1)
    required_keywords: List[str] = Field(default_factory=list)
    is_red_herring: bool = False

