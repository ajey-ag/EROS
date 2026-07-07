"""Provider interface.

Two capabilities:

- generate(prompt)   -> text. Every provider supports this. Used by decompose,
                        plan, and review.
- agent_run(spec, cwd) -> AgentResult. An autonomous coding-agent run inside a
                        working directory. Claude Code supports this natively;
                        text-only providers fall back to "degraded mode": they
                        generate a unified patch + instructions instead of
                        editing files, and the result is marked agent_mode=False
                        so the run record is honest about what happened.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AgentResult:
    success: bool
    output: str                      # final assistant text / error message
    agent_mode: bool = True          # False = degraded (patch generated, files untouched)
    cost_usd: float | None = None
    num_turns: int | None = None
    raw: dict = field(default_factory=dict)


DEGRADED_PATCH_INSTRUCTIONS = """\
You are acting as a coding agent but you CANNOT edit files directly.
Produce your complete answer as:
1. A short plan.
2. For every file to create or modify, a fenced code block preceded by a line
   `FILE: <relative/path>` containing the FULL new file content.
3. Any commands the user should run afterwards.
Be complete — the user will apply your output verbatim.
"""


class Provider(ABC):
    name: str = "base"

    def __init__(self, cfg: dict):
        self.cfg = cfg

    @property
    def model(self) -> str:
        return self.cfg.get("model", "")

    @abstractmethod
    def generate(self, prompt: str, system: str | None = None) -> str:
        """Single-shot text generation."""

    def agent_run(self, spec: str, cwd: Path) -> AgentResult:
        """Default: degraded mode — generate a patch instead of editing files."""
        text = self.generate(spec, system=DEGRADED_PATCH_INSTRUCTIONS)
        return AgentResult(success=True, output=text, agent_mode=False)
