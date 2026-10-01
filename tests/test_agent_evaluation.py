
"""Deterministic tests for AgentForge's agent interface."""

from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from app.agents.mcp_agent import AgentForge
from app.tool_logging import ToolLoggingCallback


@pytest.fixture
def anyio_backend():
    """Use asyncio for asynchronous tests."""
    return "asyncio"


@pytest.fixture
def agent():
    """Create AgentForge with a mocked agent."""
    instance = AgentForge()
    instance.agent = AsyncMock()
    return instance


@pytest.mark.anyio
async def test_agent_returns_correct_answer(agent):
    """Verify that AgentForge returns the supplied response."""

    agent.agent.ainvoke.return_value = {
        "messages": [
            AIMessage(content="The answer is 1200.")
        ]
    }

    response = await agent.ask(
        "Calculate 25 multiplied by 48.",
        session_id="eval-calculator",
    )

    assert "1200" in response


@pytest.mark.anyio
async def test_agent_configures_tool_logging(agent):
    """Verify that tool-call logging is configured."""

    agent.agent.ainvoke.return_value = {
        "messages": [
            AIMessage(content="Calculation complete.")
        ]
    }

    await agent.ask(
        "Calculate 10 multiplied by 5.",
        session_id="eval-tool-selection",
    )

    config = agent.agent.ainvoke.call_args.kwargs["config"]

    assert config["configurable"]["thread_id"] == (
        "eval-tool-selection"
    )

    assert len(config["callbacks"]) == 1

    assert isinstance(
        config["callbacks"][0],
        ToolLoggingCallback,
    )


@pytest.mark.anyio
async def test_agent_propagates_execution_errors(agent):
    """Verify that unexpected agent errors are propagated."""

    agent.agent.ainvoke.side_effect = RuntimeError(
        "Simulated agent failure"
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated agent failure",
    ):
        await agent.ask(
            "Run a calculation.",
            session_id="eval-error",
        )

