import asyncio
import sys

from mcp import Client, StdioServerParameters


async def main():
    server = StdioServerParameters(
        command=sys.executable,
        args=["app/mcp/server.py"],
    )

    async with Client(server) as client:
        print("Connected to MCP server")

        result = await client.list_tools()

        print("\nRaw tools result:")
        print(result)

        print("\nAvailable tools:")

        for tool in result.tools:
            print(f"- {tool.name}")

        tool_result = await client.call_tool(
            "employee_directory",
            {"name": "alice"},
        )

        print("\nTool result:")
        print(tool_result)


if __name__ == "__main__":
    asyncio.run(main())
