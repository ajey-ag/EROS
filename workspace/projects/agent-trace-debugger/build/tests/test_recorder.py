"""Tests for the Recorder instrumentation API."""

import pytest

from tracedbg.recorder import Recorder
from tracedbg.trace import load_trace


def test_records_two_steps_with_tool_calls(tmp_path):
    path = tmp_path / "trace.jsonl"
    with Recorder(path, agent="refagent", task="demo") as rec:
        rec.begin_step(prompt="add 1 and 2", model="fake-1")
        rec.log_tool_call("calculator", {"expr": "1+2"}, 3)
        rec.end_step(output="the answer is 3")

        rec.begin_step(prompt="count words in 'a b c'", model="fake-1")
        rec.log_tool_call("word_count", {"text": "a b c"}, 3)
        rec.log_tool_call("calculator", {"expr": "3*2"}, 6)
        rec.end_step(output="3 words, doubled is 6")

    trace = load_trace(path)
    assert trace.header.agent == "refagent"
    assert trace.header.task == "demo"
    assert len(trace.steps) == 2

    s0, s1 = trace.steps
    assert s0.index == 0
    assert s0.prompt == "add 1 and 2"
    assert s0.model == "fake-1"
    assert [(tc.name, tc.args, tc.result) for tc in s0.tool_calls] == [
        ("calculator", {"expr": "1+2"}, 3)
    ]
    assert s0.output == "the answer is 3"
    assert s0.started_at and s0.ended_at

    assert s1.index == 1
    assert [(tc.name, tc.args, tc.result) for tc in s1.tool_calls] == [
        ("word_count", {"text": "a b c"}, 3),
        ("calculator", {"expr": "3*2"}, 6),
    ]
    assert s1.output == "3 words, doubled is 6"


def test_unended_step_is_discarded(tmp_path):
    path = tmp_path / "trace.jsonl"
    with Recorder(path) as rec:
        rec.begin_step(prompt="finished", model="fake-1")
        rec.end_step(output="done")
        rec.begin_step(prompt="crashed mid-step", model="fake-1")
        rec.log_tool_call("calculator", {"expr": "1/0"}, "error")
        # context exits without end_step — simulates a crash

    trace = load_trace(path)
    assert len(trace.steps) == 1
    assert trace.steps[0].prompt == "finished"


def test_completed_steps_are_on_disk_before_close(tmp_path):
    path = tmp_path / "trace.jsonl"
    rec = Recorder(path)
    rec.begin_step(prompt="p", model="m")
    rec.end_step(output="o")
    # Readable while the recorder is still open: each step is flushed.
    trace = load_trace(path)
    assert len(trace.steps) == 1
    rec.close()


def test_log_tool_call_outside_step_raises(tmp_path):
    with Recorder(tmp_path / "trace.jsonl") as rec:
        with pytest.raises(RuntimeError):
            rec.log_tool_call("calculator", {"expr": "1"}, 1)


def test_end_step_outside_step_raises(tmp_path):
    with Recorder(tmp_path / "trace.jsonl") as rec:
        with pytest.raises(RuntimeError):
            rec.end_step(output="nope")


def test_begin_step_while_open_raises(tmp_path):
    with Recorder(tmp_path / "trace.jsonl") as rec:
        rec.begin_step(prompt="first", model="m")
        with pytest.raises(RuntimeError):
            rec.begin_step(prompt="second", model="m")


def test_empty_run_leaves_valid_trace(tmp_path):
    path = tmp_path / "trace.jsonl"
    with Recorder(path, agent="a", task="t"):
        pass
    trace = load_trace(path)
    assert trace.steps == []
    assert trace.header.created_at
