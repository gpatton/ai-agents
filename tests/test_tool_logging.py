
from uuid import uuid4
from unittest.mock import patch

import pytest

from app.tool_logging import ToolLoggingCallback


def test_successful_tool_execution():
    events = []
    callback = ToolLoggingCallback(
        request_id="test123",
        on_event=events.append,
    )
    run_id = uuid4()

    with patch(
        "app.tool_logging.perf_counter",
        side_effect=[10.0, 10.125],
    ):
        callback.on_tool_start(
            {"name": "calculator"},
            "2 + 2",
            run_id=run_id,
        )
        callback.on_tool_end(
            "4",
            run_id=run_id,
        )

    assert events[0]["type"] == "tool_start"
    assert events[1]["type"] == "tool_end"
    assert events[1]["request_id"] == "test123"
    assert events[1]["tool"] == "calculator"
    assert events[1]["duration_ms"] == pytest.approx(125.0)
    assert callback.tool_start_times == {}


def test_failed_tool_execution():
    events = []
    callback = ToolLoggingCallback(
        request_id="test456",
        on_event=events.append,
    )
    run_id = uuid4()

    with patch(
        "app.tool_logging.perf_counter",
        side_effect=[20.0, 20.075],
    ):
        callback.on_tool_start(
            {"name": "calculator"},
            "invalid input",
            run_id=run_id,
        )
        callback.on_tool_error(
            ValueError("Invalid expression"),
            run_id=run_id,
        )

    assert events[1]["type"] == "tool_error"
    assert events[1]["request_id"] == "test456"
    assert events[1]["tool"] == "calculator"
    assert events[1]["duration_ms"] == pytest.approx(75.0)
    assert callback.tool_start_times == {}


def test_missing_start_time():
    events = []
    callback = ToolLoggingCallback(
        request_id="test789",
        on_event=events.append,
    )

    callback.on_tool_end(
        "result",
        run_id=uuid4(),
    )

    assert events[0]["type"] == "tool_end"
    assert events[0]["duration_ms"] is None

