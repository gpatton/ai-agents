import logging
import uuid
from collections.abc import AsyncIterator

from langchain.mcp import MCPAdapter
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.prebuilt import create_react_agent

from app.config import settings
from app.tool_logging import ToolLoggingCallback
from app.tools.calculator import calculator
from app.tools.datetime_tool import get_current_datetime
from app.tools.document_search import search_documents
from app.tools.web_search import search_public_web


logger = logging.getLogger(__name__)


class AgentForge:
    """AgentForge AI agent with local, RAG, MCP, and persistent memory."""

    def __init__(self):
        self.adapter = None
        self.agent = None
        self.checkpointer = None
        self.checkpointer_context = None

    async def start(self) -> None:
        logger.info("Starting AgentForge")

        # Connect to PostgreSQL for persistent LangGraph checkpoints.
        self.checkpointer_context = (
            AsyncPostgresSaver.from_conn_string(
                settings.database_url
            )
        )

        self.checkpointer = (
            await self.checkpointer_context.__aenter__()
        )

        # Create/migrate LangGraph checkpoint tables.
        await self.checkpointer.setup()

        logger.info(
            "Connected to PostgreSQL checkpoint store"
        )

        # Connect to the AgentForge MCP server.
        self.adapter = MCPAdapter(
            {
                "mcpServers": {
                    "agentforge": {
                        "command": settings.mcp_server_command,
                        "args": [
                            settings.mcp_server_path,
                        ],
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
            search_public_web,
            *mcp_tools,
        ]

        model = ChatOpenAI(
            model=settings.model_name,
            temperature=0,
        )

        self.agent = create_react_agent(
            model=model,
            tools=tools,
            checkpointer=self.checkpointer,
            prompt=(
                "You are AgentForge, a helpful AI assistant. "
                "Use the available tools when necessary. "
                "For current public events, news, or schedules, use "
                "search_public_web. "
                "For questions about employees, use the "
                "employee_directory tool. "
                "For questions about company policies, benefits, "
                "procedures, or internal information, use the "
                "search_documents tool. "
                "Use the calculator tool for arithmetic when appropriate. "
                "Use the datetime tool for current date and time questions. "
                "Do not invent employee, company, or current public "
                "information. "
                "If a tool reports an error, explain the problem clearly "
                "instead of inventing a result."
            ),
        )

        logger.info("AgentForge started")

    async def ask(
        self,
        user_message: str,
        session_id: str,
    ) -> str:
        if self.agent is None:
            raise RuntimeError(
                "AgentForge has not been started."
            )

        request_id = str(uuid.uuid4())[:8]

        logger.info(
            "Agent request started | request_id=%s | "
            "session_id=%s | message=%r",
            request_id,
            session_id,
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
                "configurable": {
                    "thread_id": session_id,
                },
                "callbacks": [
                    ToolLoggingCallback(request_id),
                ],
            },
        )

        logger.info(
            "Agent request completed | request_id=%s | "
            "session_id=%s",
            request_id,
            session_id,
        )

        return result["messages"][-1].content

    async def stream(
        self,
        user_message: str,
        session_id: str,
    ) -> AsyncIterator[str]:
        """Stream an AgentForge response."""

        if self.agent is None:
            raise RuntimeError(
                "AgentForge has not been started."
            )

        request_id = str(uuid.uuid4())[:8]

        logger.info(
            "Agent stream started | request_id=%s | "
            "session_id=%s | message=%r",
            request_id,
            session_id,
            user_message,
        )

        async for message, metadata in self.agent.astream(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ]
            },
            config={
                "configurable": {
                    "thread_id": session_id,
                },
                "callbacks": [
                    ToolLoggingCallback(request_id),
                ],
            },
            stream_mode="messages",
        ):
            content = getattr(
                message,
                "content",
                None,
            )

            if isinstance(content, str) and content:
                yield content

        logger.info(
            "Agent stream completed | request_id=%s | "
            "session_id=%s",
            request_id,
            session_id,
        )

    async def delete_conversation(
        self,
        session_id: str,
    ) -> None:
        """Delete persisted LangGraph state for a conversation."""

        if self.checkpointer is None:
            raise RuntimeError(
                "AgentForge has not been started."
            )

        await self.checkpointer.adelete_thread(
            session_id
        )

        logger.info(
            "Conversation state deleted | session_id=%s",
            session_id,
        )

    async def close(self) -> None:
        logger.info("Stopping AgentForge")

        if self.adapter is not None:
            await self.adapter.__aexit__(
                None,
                None,
                None,
            )

        if self.checkpointer_context is not None:
            await self.checkpointer_context.__aexit__(
                None,
                None,
                None,
            )

        self.agent = None
        self.adapter = None
        self.checkpointer = None
        self.checkpointer_context = None

        logger.info("AgentForge stopped")
