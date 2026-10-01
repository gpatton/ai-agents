
"""Local JSON reporting for AgentForge evaluations."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPORT_DIR = Path("reports")


def save_evaluation_report(
    test_name: str,
    passed: bool,
    response: str,
    response_time_seconds: float,
    tool_events: list[dict[str, Any]],
) -> Path:
    """Save one evaluation result without overwriting previous runs."""

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    filename = (
        f"{test_name}_"
        f"{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    )

    tool_executions = [
        {
            "tool": event.get("tool"),
            "run_id": event.get("run_id"),
            "duration_ms": event.get("duration_ms"),
            "event_type": event.get("type"),
        }
        for event in tool_events
        if event.get("type") in ("tool_end", "tool_error")
    ]

    report = {
        "test_name": test_name,
        "timestamp": timestamp.isoformat(),
        "passed": passed,
        "response": response,
        "response_time_seconds": round(
            response_time_seconds, 3
        ),
        "tool_executions": tool_executions,
    }

    destination = REPORT_DIR / filename

    destination.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return destination

