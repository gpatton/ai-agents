
"""Live AgentForge evaluations with JSON reporting.

Run explicitly:
    RUN_LIVE_EVAL=1 python -m pytest \
        tests/live/test_live_agent.py -v -s
"""

import os
from time import perf_counter
from uuid import uuid4

import pytest

from app.agents.mcp_agent import AgentForge
from app.evaluation.report import save_evaluation_report


pytestmark = pytest.mark.anyio

LIVE_ENABLED = os.getenv("RUN_LIVE_EVAL") == "1"

live_only = pytest.mark.skipif(
    not LIVE_ENABLED,
    reason="Live evaluation requires explicit opt-in",
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def run_evaluation(
    test_name: str,
    prompt: str,
    validate,
):
    """Run a live evaluation and save its JSON report."""

    agent = AgentForge()
    events = []
    response_chunks = []

    session_id = f"{test_name}-{uuid4()}"

    started = False
    passed = False
    answer = ""
    elapsed_seconds = 0.0
    error_message = None
    start_time = None

    try:
        await agent.start()
        started = True

        start_time = perf_counter()

        async for chunk in agent.stream(
            user_message=prompt,
            session_id=session_id,
            on_tool_event=events.append,
        ):
            response_chunks.append(chunk)

        elapsed_seconds = perf_counter() - start_time
        answer = "".join(response_chunks)

        print(f"\nEvaluation: {test_name}")
        print(f"Agent response: {answer}")
        print(f"Response time: {elapsed_seconds:.2f} seconds")
        print(f"Tool events: {events}")

        validate(answer, events)

        passed = True

    except Exception as error:
        error_message = str(error)
        raise

    finally:
        if start_time is not None:
            elapsed_seconds = perf_counter() - start_time

        answer = "".join(response_chunks)

        try:
            if started:
                await agent.close()

        finally:
            report_path = save_evaluation_report(
                test_name=test_name,
                passed=passed,
                response=answer,
                response_time_seconds=elapsed_seconds,
                tool_events=events,
            )

            print(f"\nEvaluation report: {report_path}")

            if error_message:
                print(f"Evaluation error: {error_message}")


def validate_calculator(answer, events):
    """Validate arithmetic accuracy and calculator selection."""

    calculator_events = [
        event
        for event in events
        if event.get("tool") == "calculator"
    ]

    completed = [
        event
        for event in calculator_events
        if event.get("type") == "tool_end"
    ]

    assert "1200" in answer.replace(",", ""), (
        "Agent did not return the expected result."
    )

    assert any(
        event.get("type") == "tool_start"
        for event in calculator_events
    ), "Agent did not select the calculator tool."

    assert completed, (
        "Calculator did not emit a completion event."
    )

    assert any(
        isinstance(event.get("duration_ms"), (int, float))
        for event in completed
    ), "Calculator execution timing was not recorded."


def validate_document_retrieval(answer, events):
    """Validate handbook retrieval and answer accuracy."""

    search_events = [
        event
        for event in events
        if event.get("tool") == "search_documents"
    ]

    completed = [
        event
        for event in search_events
        if event.get("type") == "tool_end"
    ]

    assert "25" in answer, (
        "Agent did not return the correct leave entitlement."
    )

    assert any(
        event.get("type") == "tool_start"
        for event in search_events
    ), "Agent did not select search_documents."

    assert completed, (
        "Document search did not complete."
    )

    assert any(
        "25 days" in event.get("output", "")
        for event in completed
    ), "Retrieved content did not contain the expected policy."

    assert any(
        isinstance(event.get("duration_ms"), (int, float))
        for event in completed
    ), "Document retrieval timing was not recorded."


def validate_error_recovery(answer, events):
    """Validate division-by-zero error handling."""

    calculator_events = [
        event
        for event in events
        if event.get("tool") == "calculator"
    ]

    completed = [
        event
        for event in calculator_events
        if event.get("type") == "tool_end"
    ]

    assert any(
        event.get("type") == "tool_start"
        for event in calculator_events
    ), "Agent did not select the calculator."

    assert any(
        "Cannot divide by zero" in event.get("output", "")
        for event in completed
    ), "Calculator error was not reported."

    assert any(
        phrase in answer.lower()
        for phrase in [
            "divide by zero",
            "division by zero",
            "undefined",
        ]
    ), "Agent did not explain the division-by-zero error."

    assert any(
        isinstance(event.get("duration_ms"), (int, float))
        for event in completed
    ), "Tool execution timing was not recorded."


@live_only
async def test_live_calculator_evaluation():
    """Evaluate real calculator usage."""

    await run_evaluation(
        test_name="live_calculator",
        prompt=(
            "Use the calculator tool to multiply "
            "25 by 48. Report the numerical answer."
        ),
        validate=validate_calculator,
    )


@live_only
async def test_live_document_retrieval():
    """Evaluate real RAG document retrieval."""

    await run_evaluation(
        test_name="live_document_retrieval",
        prompt=(
            "According to the AgentForge employee handbook, "
            "how many days of paid annual leave do employees "
            "receive per year? Use search_documents."
        ),
        validate=validate_document_retrieval,
    )


@live_only
async def test_live_calculator_error_recovery():
    """Evaluate division-by-zero error recovery."""

    await run_evaluation(
        test_name="live_calculator_error_recovery",
        prompt=(
            "Use the calculator tool to divide 100 by 0. "
            "Explain the result. Do not invent an answer."
        ),
        validate=validate_error_recovery,
    )

