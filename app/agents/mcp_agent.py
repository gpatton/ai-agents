import sys

from langchain.mcp import MCPAdapter
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.tools.calculator import calculator
from app.tools.datetime_tool import get_current_datetime
from app.tools.document_search import search_documents


async def run_mcp_agent(user_message: str) -> str:
    adapter = MCPAdapter(
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
    mcp_tools = await adapter.list_tools()

    print(
        "MCP tools:",
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

    agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=(
            "You are AgentForge, a helpful AI assistant. "
            "Use the available tools when necessary. "
            "For questions about employees, use the "
            "employee_directory tool. "
            "For questions about company policies, benefits, "
            "procedures, or internal information, use the "
            "document search tool. "
            "Do not invent employee or company information."
        ),
    )

    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_message,
                }
            ]
        }
    )

    return result["messages"][-1].content
