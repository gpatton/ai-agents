import logging
import sys
import uuid

from langchain.mcp import MCPAdapter
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.tool_logging import ToolLoggingCallback
from app.tools.calculator import calculator
from app.tools.datetime_tool import get_current_datetime
from app.tools.document_search import search_documents


logger = logging.getLogger(__name__)


class AgentForge:
    """AgentForge AI agent with local, RAG, and MCP tools."""

    def __init__(self):
        self.adapter = None
        self.agent = None

    async def start(self) -> None:
        """Initialize MCP and build the LangGraph agent."""

        logger.info("Starting AgentForge")

        self.adapter = MCPAdapter(
            {
                "mcpServers": {
                    "agentforge": {
                        "command": sys.executable,
                        "args": ["app/mcp/server.py"],
                        "transport": "stdio",
                    }
                }
            }
        )

        await self.adapter.__aenter__()

        logger.info("Connected to MCP server")

        mcp_tools = await self.adapter.list_tools()

        logger.info(
            "MCP tools discovered | tools=%s",
            [tool.name for tool in mcp_tools],
        )

        tools = [
            calculator,
            get_current_datetime,
            search_documents,
            *mcp_tools,
        ]

        model = ChatOpenAI(
            model="gpt-5.4-mini",
            temperature=0,
        )

        self.agent = create_react_agent(
            model=model,
            tools=tools,
            prompt=(
                "You are AgentForge, a helpful AI assistant. "
                "Use the available tools when necessary. "
                "For questions about employees, use the "
                "employee_directory tool. "
                "For questions about company policies, benefits, "
                "procedures, or internal information, use the "
                "search_documents tool. "
                "Use the calculator tool for arithmetic when appropriate. "
                "Use the datetime tool for current date and time questions. "
                "Do not invent employee or company information. "
                "If a tool reports an error, explain the problem clearly "
                "instead of inventing a result."
            ),
        )

        logger.info("AgentForge started")

    async def ask(self, user_message: str) -> str:
        """Send a message to AgentForge."""

        if self.agent is None:
            raise RuntimeError(
                "AgentForge has not been started."
            )

        request_id = str(uuid.uuid4())[:8]

        logger.info(
            "Agent request started | request_id=%s | message=%r",
            request_id,
            user_message,
        )

        result = await self.agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ]
            },
            config={
                "callbacks": [
                    ToolLoggingCallback(request_id),
                ]
            },
        )

        logger.info(
            "Agent request completed | request_id=%s",
            request_id,
        )

        return result["messages"][-1].content

    async def close(self) -> None:
        """Shut down AgentForge and its MCP connection."""

        logger.info("Stopping AgentForge")

        if self.adapter is not None:
            await self.adapter.__aexit__(
                None,
                None,
                None,
            )

        self.agent = None
        self.adapter = None

        logger.info("AgentForge stopped")
