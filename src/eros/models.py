"""Core data model: Idea -> Project -> Task -> Run -> Experiment.

Everything serializes to markdown-with-frontmatter or YAML so the workspace
stays readable without EROS installed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

SCORE_AXES = ["originality", "technical_depth", "interview_value", "startup_potential", "reuse"]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Scores(BaseModel):
    originality: int = Field(ge=1, le=5)
    technical_depth: int = Field(ge=1, le=5)
    interview_value: int = Field(ge=1, le=5)
    startup_potential: int = Field(ge=1, le=5)
    reuse: int = Field(ge=1, le=5)

    @property
    def total(self) -> int:
        return sum(getattr(self, axis) for axis in SCORE_AXES)


class Idea(BaseModel):
    id: str
    title: str
    domain: str
    pitch: str
    scores: Scores
    flagship_candidate: bool = False
    status: str = "mapped"  # mapped | promoted

    @property
    def total(self) -> int:
        return self.scores.total


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    needs_review = "needs_review"
    needs_revision = "needs_revision"
    done = "done"
    blocked = "blocked"


class Task(BaseModel):
    id: str
    title: str
    status: TaskStatus = TaskStatus.todo
    depends_on: list[str] = []
    runs: list[str] = []
    created: str = Field(default_factory=now_iso)
    # body of the markdown file (description + acceptance criteria) is kept
    # alongside, not in the model


class RunStatus(str, Enum):
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class ReviewVerdict(str, Enum):
    approve = "approve"
    revise = "revise"
    pending = "pending"


class Run(BaseModel):
    id: str
    task_id: str
    provider: str
    model: str = ""
    status: RunStatus = RunStatus.running
    started: str = Field(default_factory=now_iso)
    finished: str = ""
    cost_usd: float | None = None
    num_turns: int | None = None
    agent_mode: bool = True  # False = provider only generated a patch/instructions
    review: ReviewVerdict = ReviewVerdict.pending


class Project(BaseModel):
    slug: str
    idea_id: str
    title: str
    status: str = "active"  # active | paused | shipped
    created: str = Field(default_factory=now_iso)


class Experiment(BaseModel):
    ts: str = Field(default_factory=now_iso)
    name: str
    metrics: dict[str, float] = {}
    params: dict[str, str] = {}
    notes: str = ""
