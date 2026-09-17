from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages


class ConversationState(TypedDict):
    messages: Annotated[list, add_messages]


def respond(state: ConversationState):
    """Return a deterministic response based on conversation history."""

    messages = state["messages"]

    current_message = messages[-1].content.lower()

    previous_text = " ".join(
        message.content.lower()
        for message in messages[:-1]
    )

    if "alice" in current_message:
        response = "Alice Murphy is an AI Engineer."

    elif (
        "what department is she in" in current_message
        and "alice" in previous_text
    ):
        response = "She is in the Engineering department."

    else:
        response = "I do not know who you mean."

    return {
        "messages": [
            AIMessage(content=response),
        ]
    }


def create_test_graph():
    builder = StateGraph(ConversationState)

    builder.add_node("respond", respond)

    builder.set_entry_point("respond")
    builder.add_edge("respond", END)

    return builder.compile(
        checkpointer=InMemorySaver()
    )


def test_same_session_remembers_context():
    graph = create_test_graph()

    config = {
        "configurable": {
            "thread_id": "conversation-1",
        }
    }

    graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="Who is Alice?"
                )
            ]
        },
        config=config,
    )

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="What department is she in?"
                )
            ]
        },
        config=config,
    )

    assert (
        result["messages"][-1].content
        == "She is in the Engineering department."
    )


def test_different_sessions_are_isolated():
    graph = create_test_graph()

    first_session = {
        "configurable": {
            "thread_id": "conversation-1",
        }
    }

    second_session = {
        "configurable": {
            "thread_id": "conversation-2",
        }
    }

    graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="Who is Alice?"
                )
            ]
        },
        config=first_session,
    )

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="What department is she in?"
                )
            ]
        },
        config=second_session,
    )

    assert (
        result["messages"][-1].content
        == "I do not know who you mean."
    )
