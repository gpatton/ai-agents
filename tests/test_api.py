from fastapi.testclient import TestClient

from app.api import (
    app,
    get_agent,
    get_conversation_repository,
    get_message_repository,
)
from app.conversations import create_conversation


class FakeAgent:
    def __init__(self):
        self.agent = object()

    async def ask(
        self,
        message: str,
        session_id: str,
    ) -> str:
        return f"Test response: {message}"

    async def stream(
        self,
        message: str,
        session_id: str,
    ):
        yield "Hello "
        yield "from "
        yield "AgentForge"

    async def delete_conversation(
        self,
        session_id: str,
    ) -> None:
        pass


class FakeConversationRepository:
    def __init__(self):
        self.conversations = {}

    async def rename(self, conversation_id: str, title: str):
        conversation = self.conversations.get(conversation_id)

        if conversation is None:
            return None

        conversation.title = title
        return conversation


    async def save(
        self,
        conversation,
    ):
        self.conversations[
            conversation.id
        ] = conversation

    async def get(
        self,
        conversation_id,
    ):
        return self.conversations.get(
            conversation_id
        )

    async def list_all(self):
        return list(
            self.conversations.values()
        )

    async def delete(
        self,
        conversation_id,
    ):
        return (
            self.conversations.pop(
                conversation_id,
                None,
            )
            is not None
        )


class FakeMessageRepository:
    def __init__(self):
        self.messages = []

    async def save(
        self,
        message,
    ):
        self.messages.append(
            message
        )

    async def list_for_conversation(
        self,
        conversation_id,
    ):
        return [
            message
            for message in self.messages
            if message.conversation_id
            == conversation_id
        ]


def override_get_agent():
    return FakeAgent()


fake_repository = FakeConversationRepository()
fake_message_repository = FakeMessageRepository()


test_conversation = create_conversation(
    "Test conversation"
)

test_conversation.id = "test-session"

fake_repository.conversations[
    test_conversation.id
] = test_conversation


def override_get_conversation_repository():
    return fake_repository


def override_get_message_repository():
    return fake_message_repository


app.dependency_overrides[
    get_agent
] = override_get_agent

app.dependency_overrides[
    get_conversation_repository
] = override_get_conversation_repository

app.dependency_overrides[
    get_message_repository
] = override_get_message_repository


def test_health():
    client = TestClient(app)

    response = client.get(
        "/health"
    )

    assert response.status_code == 200

    assert response.json() == {
        "status": "healthy",
        "service": "AgentForge",
    }


def test_ready():
    client = TestClient(app)

    response = client.get(
        "/ready"
    )

    assert response.status_code == 200

    assert response.json() == {
        "status": "ready",
        "service": "AgentForge",
    }


def test_chat():
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "message": "Hello AgentForge",
            "session_id": "test-session",
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        "response": (
            "Test response: Hello AgentForge"
        ),
    }


def test_chat_unknown_conversation_returns_404():
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "message": "Hello AgentForge",
            "session_id": "does-not-exist",
        },
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Conversation not found.",
    }


def test_empty_message_is_rejected():
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "message": "",
            "session_id": "test-session",
        },
    )

    assert response.status_code == 422


def test_message_over_max_length_is_rejected():
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "message": "a" * 4001,
            "session_id": "test-session",
        },
    )

    assert response.status_code == 422


def test_missing_session_id_is_rejected():
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "message": "Hello AgentForge",
        },
    )

    assert response.status_code == 422


def test_empty_session_id_is_rejected():
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "message": "Hello AgentForge",
            "session_id": "",
        },
    )

    assert response.status_code == 422


def test_create_conversation():
    client = TestClient(app)

    response = client.post(
        "/conversations",
        json={
            "title": "Employee questions",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["title"] == "Employee questions"
    assert data["id"]
    assert data["created_at"]


def test_get_conversation():
    client = TestClient(app)

    response = client.get(
        "/conversations/test-session"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == "test-session"
    assert data["title"] == "Test conversation"
    assert data["created_at"]


def test_get_unknown_conversation_returns_404():
    client = TestClient(app)

    response = client.get(
        "/conversations/does-not-exist"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Conversation not found.",
    }


def test_list_conversations():
    client = TestClient(app)

    response = client.get(
        "/conversations"
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(
        data,
        list,
    )

    assert any(
        conversation["id"]
        == "test-session"
        for conversation in data
    )


def test_delete_conversation():
    client = TestClient(app)

    conversation = create_conversation(
        "Conversation to delete"
    )

    fake_repository.conversations[
        conversation.id
    ] = conversation

    response = client.delete(
        f"/conversations/{conversation.id}"
    )

    assert response.status_code == 204

    assert (
        conversation.id
        not in fake_repository.conversations
    )


def test_delete_unknown_conversation_returns_404():
    client = TestClient(app)

    response = client.delete(
        "/conversations/unknown-conversation"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Conversation not found.",
    }


def test_chat_saves_messages():
    client = TestClient(app)

    fake_message_repository.messages.clear()

    response = client.post(
        "/chat",
        json={
            "message": "Who is Alice?",
            "session_id": "test-session",
        },
    )

    assert response.status_code == 200

    assert len(
        fake_message_repository.messages
    ) == 2

    user_message = (
        fake_message_repository.messages[0]
    )

    assistant_message = (
        fake_message_repository.messages[1]
    )

    assert user_message.role == "user"
    assert (
        user_message.content
        == "Who is Alice?"
    )

    assert (
        user_message.conversation_id
        == "test-session"
    )

    assert assistant_message.role == "assistant"

    assert (
        assistant_message.content
        == "Test response: Who is Alice?"
    )

    assert (
        assistant_message.conversation_id
        == "test-session"
    )
def test_get_conversation_messages():
    client = TestClient(app)

    fake_message_repository.messages.clear()

    chat_response = client.post(
        "/chat",
        json={
            "message": "Who is Alice?",
            "session_id": "test-session",
        },
    )

    assert chat_response.status_code == 200

    response = client.get(
        "/conversations/test-session/messages"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["conversation_id"] == "test-session"
    assert len(data["messages"]) == 2

    assert data["messages"][0]["role"] == "user"
    assert (
        data["messages"][0]["content"]
        == "Who is Alice?"
    )

    assert data["messages"][1]["role"] == "assistant"
    assert (
        data["messages"][1]["content"]
        == "Test response: Who is Alice?"
    )


def test_get_messages_unknown_conversation_returns_404():
    client = TestClient(app)

    response = client.get(
        "/conversations/does-not-exist/messages"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Conversation not found.",
    }

def test_stream_chat():
    client = TestClient(app)

    fake_message_repository.messages.clear()

    response = client.post(
        "/chat/stream",
        json={
            "message": "Hello",
            "session_id": "test-session",
        },
    )

    assert response.status_code == 200

    assert (
        response.text
        == "Hello from AgentForge"
    )

    assert len(
        fake_message_repository.messages
    ) == 2

    assert (
        fake_message_repository.messages[0].content
        == "Hello"
    )

    assert (
        fake_message_repository.messages[1].content
        == "Hello from AgentForge"
    )
def test_stream_unknown_conversation_returns_404():
    client = TestClient(app)

    response = client.post(
        "/chat/stream",
        json={
            "message": "Hello",
            "session_id": "does-not-exist",
        },
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Conversation not found.",
    }

async def rename(
    self,
    conversation_id: str,
    title: str,
):
    conversation = self.conversations.get(
        conversation_id
    )

    if conversation is None:
        return None

    conversation.title = title
    return conversation


def test_rename_conversation():
    client = TestClient(app)

    response = client.patch(
        "/conversations/test-session",
        json={
            "title": "Employee policy questions",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == "test-session"
    assert data["title"] == "Employee policy questions"
    assert data["created_at"]

    stored_conversation = (
        fake_repository.conversations["test-session"]
    )

    assert (
        stored_conversation.title
        == "Employee policy questions"
    )


def test_rename_unknown_conversation_returns_404():
    client = TestClient(app)

    response = client.patch(
        "/conversations/does-not-exist",
        json={
            "title": "Updated title",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Conversation not found.",
    }


def test_rename_conversation_rejects_empty_title():
    client = TestClient(app)

    response = client.patch(
        "/conversations/test-session",
        json={
            "title": "",
        },
    )

    assert response.status_code == 422


def test_rename_conversation_rejects_long_title():
    client = TestClient(app)

    response = client.patch(
        "/conversations/test-session",
        json={
            "title": "A" * 201,
        },
    )

    assert response.status_code == 422
