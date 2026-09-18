from fastapi.testclient import TestClient

from app.api import (
    app,
    get_agent,
    get_conversation_repository,
)
from app.conversations import create_conversation


class FakeAgent:
    def __init__(self):
        self.agent = object()

    async def delete_conversation(
        self,

        session_id: str,
        ) -> None:
        pass

    async def ask(
        self,
        message: str,
        session_id: str,
    ) -> str:
        return f"Test response: {message}"


class FakeConversationRepository:
    def __init__(self):
        self.conversations = {}

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


def override_get_agent():
    return FakeAgent()


fake_repository = FakeConversationRepository()

test_conversation = create_conversation(
    "Test conversation"
)

# Give the test conversation a predictable ID.
test_conversation.id = "test-session"

fake_repository.conversations[
    test_conversation.id
] = test_conversation


def override_get_conversation_repository():
    return fake_repository


app.dependency_overrides[
    get_agent
] = override_get_agent

app.dependency_overrides[
    get_conversation_repository
] = override_get_conversation_repository


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

    assert isinstance(data, list)

    assert any(
        conversation["id"] == "test-session"
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
