from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.tools.calculator import calculator
from app.tools.datetime_tool import get_current_datetime
from app.tools.document_search import search_documents


model = ChatOpenAI(
    model="gpt-5.4-mini",
    temperature=0,
)


agent = create_react_agent(
    model=model,
    tools=[
        calculator,
        get_current_datetime,
        search_documents,
    ],
    prompt=(
        "You are AgentForge, a helpful AI assistant. "
        "Use the available tools when necessary. "
        "For questions about company policies, benefits, procedures, "
        "or internal information, search the company documents before "
        "answering. Base company-related answers only on information "
        "returned by the document search tool. "
        "If the documents do not contain enough information, say so."
    ),
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
