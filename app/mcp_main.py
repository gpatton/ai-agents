import asyncio

from dotenv import load_dotenv

load_dotenv()

from app.agents.mcp_agent import run_mcp_agent


async def main():
    print("AgentForge — MCP")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ")

        if user_input.lower() == "quit":
            break

        answer = await run_mcp_agent(user_input)

        print(f"Agent: {answer}\n")


if __name__ == "__main__":
    asyncio.run(main())
