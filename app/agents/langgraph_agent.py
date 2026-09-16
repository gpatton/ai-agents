from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.prebuilt import create_react_agent


@tool
def calculator(a: float, b: float, operation: str) -> float:
    """Perform a basic arithmetic operation."""

    if operation == "add":
        return a + b

    if operation == "subtract":
        return a - b

    if operation == "multiply":
        return a * b

    if operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero.")
        return a / b

    raise ValueError(f"Unknown operation: {operation}")


@tool
def get_current_datetime(timezone: str) -> str:
    """Get the current date and time for an IANA timezone."""

    try:
        current_time = datetime.now(ZoneInfo(timezone))

        return current_time.strftime(
            "%A, %d %B %Y at %H:%M:%S %Z"
        )

    except Exception:
        return f"Invalid timezone: {timezone}"


model = ChatOpenAI(
    model="gpt-5.4-mini",
    temperature=0,
)

agent = create_react_agent(
    model=model,
    tools=[
        calculator,
        get_current_datetime,
    ],
)


def run_langgraph_agent(user_message: str) -> str:

    result = agent.invoke(
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
