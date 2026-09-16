from dotenv import load_dotenv

from app.agents.agent import run_agent


load_dotenv()


def main():
    print("AgentForge")
    print("Type 'quit' to exit.\n")

    while True:

        user_input = input("You: ")

        if user_input.lower() == "quit":
            break

        answer = run_agent(user_input)

        print(f"Agent: {answer}\n")


if __name__ == "__main__":
    main()
