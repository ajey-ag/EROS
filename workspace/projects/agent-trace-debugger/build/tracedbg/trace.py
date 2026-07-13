"""Trace schema and JSONL store.

The trace file is the public contract of tracedbg: one JSON object per line,
a header record first, then one step record per completed agent step. See
docs/trace-format.md for the full schema.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

KNOWN_SCHEMA_VERSIONS = {1}


@dataclass
class ToolCall:
    name: str
    args: dict
    result: object

    def to_json(self) -> dict:
        return {"name": self.name, "args": self.args, "result": self.result}

    @classmethod
    def from_json(cls, data: dict) -> "ToolCall":
        return cls(
            name=data["name"],
            args=data["args"],
            result=data.get("result"),
        )


@dataclass
class Step:
    index: int
    prompt: str
    model: str
    tool_calls: list[ToolCall]
    output: str
    started_at: str
    ended_at: str

    def to_json(self) -> dict:
        return {
            "type": "step",
            "index": self.index,
            "prompt": self.prompt,
            "model": self.model,
            "tool_calls": [tc.to_json() for tc in self.tool_calls],
            "output": self.output,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }

    @classmethod
    def from_json(cls, data: dict) -> "Step":
        return cls(
            index=data["index"],
            prompt=data["prompt"],
            model=data["model"],
            tool_calls=[ToolCall.from_json(tc) for tc in data["tool_calls"]],
            output=data["output"],
            started_at=data["started_at"],
            ended_at=data["ended_at"],
        )


@dataclass
class TraceHeader:
    schema_version: int
    created_at: str
    agent: str
    task: str

    def to_json(self) -> dict:
        return {
            "type": "header",
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "agent": self.agent,
            "task": self.task,
        }

    @classmethod
    def from_json(cls, data: dict) -> "TraceHeader":
        return cls(
            schema_version=data["schema_version"],
            created_at=data["created_at"],
            agent=data.get("agent", ""),
            task=data.get("task", ""),
        )


@dataclass
class Trace:
    header: TraceHeader
    steps: list[Step] = field(default_factory=list)


def _dump_line(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, separators=(", ", ": "))


class TraceWriter:
    """Append-only JSONL writer. Writes the header on open and flushes each
    step immediately, so a crash mid-run leaves a valid partial trace.
    """

    def __init__(self, path: str | Path, header: TraceHeader | None = None):
        self.path = Path(path)
        if header is None:
            header = TraceHeader(
                schema_version=SCHEMA_VERSION, created_at="", agent="", task=""
            )
        if header.schema_version not in KNOWN_SCHEMA_VERSIONS:
            raise ValueError(
                f"unknown schema_version: {header.schema_version!r}"
            )
        self.header = header
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("w", encoding="utf-8", newline="\n")
        self._file.write(_dump_line(header.to_json()) + "\n")
        self._file.flush()

    def append(self, step: Step) -> None:
        if self._file.closed:
            raise ValueError("TraceWriter is closed")
        self._file.write(_dump_line(step.to_json()) + "\n")
        self._file.flush()

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()

    def __enter__(self) -> "TraceWriter":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()


def load_trace(path: str | Path) -> Trace:
    """Parse a JSONL trace file into a Trace.

    Tolerates unknown fields on any record. Raises ValueError on malformed
    JSON lines, a missing or invalid header, or an unknown schema version.
    """
    path = Path(path)
    header: TraceHeader | None = None
    steps: list[Step] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{lineno}: malformed JSON: {e}") from e
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{lineno}: record is not a JSON object")

            if header is None:
                if record.get("type") != "header":
                    raise ValueError(
                        f"{path}:{lineno}: first record must be a header, "
                        f"got type={record.get('type')!r}"
                    )
                if record.get("schema_version") not in KNOWN_SCHEMA_VERSIONS:
                    raise ValueError(
                        f"{path}:{lineno}: unknown schema_version: "
                        f"{record.get('schema_version')!r}"
                    )
                header = TraceHeader.from_json(record)
                continue

            record_type = record.get("type")
            if record_type == "step":
                try:
                    steps.append(Step.from_json(record))
                except (KeyError, TypeError) as e:
                    raise ValueError(
                        f"{path}:{lineno}: invalid step record: {e}"
                    ) from e
            else:
                # Unknown record types are tolerated for forward compatibility.
                continue

    if header is None:
        raise ValueError(f"{path}: trace file has no header record")
    return Trace(header=header, steps=steps)
