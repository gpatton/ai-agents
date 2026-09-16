from dotenv import load_dotenv

load_dotenv()

from app.agents.langgraph_agent import run_langgraph_agent


def main():
    print("AgentForge — LangGraph")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ")

        if user_input.lower() == "quit":
            break

        answer = run_langgraph_agent(user_input)

        print(f"Agent: {answer}\n")


if __name__ == "__main__":
    main()
