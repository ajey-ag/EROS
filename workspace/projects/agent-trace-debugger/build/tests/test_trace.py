import json

import pytest

from tracedbg.trace import (
    SCHEMA_VERSION,
    Step,
    ToolCall,
    TraceHeader,
    TraceWriter,
    load_trace,
)


def make_step(index: int) -> Step:
    return Step(
        index=index,
        prompt=f"prompt {index}",
        model="fake-model",
        tool_calls=[
            ToolCall(
                name="calculator",
                args={"expression": f"{index}+{index}"},
                result=index * 2,
            )
        ],
        output=f"output {index}",
        started_at=f"2026-07-13T10:00:0{index}+00:00",
        ended_at=f"2026-07-13T10:00:0{index + 1}+00:00",
    )


def make_header() -> TraceHeader:
    return TraceHeader(
        schema_version=SCHEMA_VERSION,
        created_at="2026-07-13T10:00:00+00:00",
        agent="refagent",
        task="test task",
    )


def test_round_trip(tmp_path):
    path = tmp_path / "trace.jsonl"
    steps = [make_step(i) for i in range(3)]
    with TraceWriter(path, header=make_header()) as w:
        for step in steps:
            w.append(step)

    trace = load_trace(path)
    assert trace.header == make_header()
    assert trace.steps == steps


def test_unknown_extra_field_tolerated(tmp_path):
    path = tmp_path / "trace.jsonl"
    with TraceWriter(path, header=make_header()) as w:
        w.append(make_step(0))

    # Inject an unknown field into both the header and the step line.
    lines = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
    lines[0]["future_header_field"] = True
    lines[1]["token_count"] = 42
    path.write_text(
        "".join(json.dumps(l) + "\n" for l in lines), encoding="utf-8"
    )

    trace = load_trace(path)
    assert len(trace.steps) == 1
    assert trace.steps[0] == make_step(0)


def test_missing_header_raises(tmp_path):
    path = tmp_path / "trace.jsonl"
    path.write_text(
        json.dumps(make_step(0).to_json()) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError):
        load_trace(path)


def test_empty_file_raises(tmp_path):
    path = tmp_path / "trace.jsonl"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        load_trace(path)


def test_malformed_line_raises(tmp_path):
    path = tmp_path / "trace.jsonl"
    with TraceWriter(path, header=make_header()) as w:
        w.append(make_step(0))
    with path.open("a", encoding="utf-8") as f:
        f.write("{not json\n")
    with pytest.raises(ValueError):
        load_trace(path)


def test_unknown_schema_version_raises(tmp_path):
    path = tmp_path / "trace.jsonl"
    header = make_header().to_json()
    header["schema_version"] = 999
    path.write_text(json.dumps(header) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_trace(path)


def test_partial_trace_loads(tmp_path):
    path = tmp_path / "trace.jsonl"
    w = TraceWriter(path, header=make_header())
    w.append(make_step(0))
    # Simulate a crash: writer never closed, no further lines written.
    trace = load_trace(path)
    assert len(trace.steps) == 1
    assert trace.steps[0] == make_step(0)
    w.close()
