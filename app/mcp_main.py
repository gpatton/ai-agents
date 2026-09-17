import asyncio

from dotenv import load_dotenv

from app.agents.mcp_agent import AgentForge
from app.logging_config import setup_logging


load_dotenv()


async def main():
    agent = AgentForge()

    await agent.start()

    print("AgentForge — MCP")
    print("Type 'quit' to exit.\n")

    try:
        while True:
            user_input = input("You: ")

            if user_input.lower() == "quit":
                break

            try:
                answer = await agent.ask(user_input)
                print(f"Agent: {answer}\n")

            except Exception:
                print(
                    "Agent: Something went wrong while processing "
                    "your request. Please try again.\n"
                )

    finally:
        await agent.close()


if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())
