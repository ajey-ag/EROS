"""Recorder instrumentation API.

An agent calls the Recorder at step boundaries; each completed step is
flushed to the trace file immediately, so a crash mid-step leaves a valid
trace containing only the steps that finished.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .trace import SCHEMA_VERSION, Step, ToolCall, TraceHeader, TraceWriter


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Recorder:
    """Records an agent execution to a JSONL trace file.

    Usage:

        with Recorder("trace.jsonl", agent="refagent", task="demo") as rec:
            rec.begin_step(prompt="...", model="fake")
            rec.log_tool_call("calc", {"expr": "1+1"}, 2)
            rec.end_step(output="2")

    An open step that is never ended is discarded on close; only completed
    steps appear on disk.
    """

    def __init__(self, path: str | Path, agent: str = "", task: str = ""):
        header = TraceHeader(
            schema_version=SCHEMA_VERSION,
            created_at=_now_iso(),
            agent=agent,
            task=task,
        )
        self._writer = TraceWriter(path, header)
        self._next_index = 0
        self._open_step: Step | None = None

    @property
    def path(self) -> Path:
        return self._writer.path

    def begin_step(self, prompt: str, model: str) -> None:
        if self._open_step is not None:
            raise RuntimeError(
                f"step {self._open_step.index} is already open; "
                "call end_step before beginning another"
            )
        self._open_step = Step(
            index=self._next_index,
            prompt=prompt,
            model=model,
            tool_calls=[],
            output="",
            started_at=_now_iso(),
            ended_at="",
        )

    def log_tool_call(self, name: str, args: dict, result: object) -> None:
        if self._open_step is None:
            raise RuntimeError("no step is open; call begin_step first")
        self._open_step.tool_calls.append(
            ToolCall(name=name, args=args, result=result)
        )

    def end_step(self, output: str) -> None:
        if self._open_step is None:
            raise RuntimeError("no step is open; call begin_step first")
        step = self._open_step
        step.output = output
        step.ended_at = _now_iso()
        self._writer.append(step)
        self._open_step = None
        self._next_index += 1

    def close(self) -> None:
        # An unfinished step is intentionally discarded: the trace on disk
        # contains only completed steps.
        self._open_step = None
        self._writer.close()

    def __enter__(self) -> "Recorder":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()
