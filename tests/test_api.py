from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.api import (
    app,
    get_agent,
    get_conversation_repository,
    get_message_repository,
    get_registered_user_id,
)
from app.conversations import create_conversation


TEST_USER_ID = "user_test_123"
OTHER_USER_ID = "user_other_456"


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

    async def save(self, conversation):
        self.conversations[conversation.id] = conversation

    async def get(
        self,
        conversation_id: str,
        user_id: str,
    ):
        conversation = self.conversations.get(conversation_id)

        if conversation is None or conversation.user_id != user_id:
            return None

        return conversation

    async def rename(
        self,
        conversation_id: str,
        title: str,
        user_id: str,
    ):
        conversation = await self.get(conversation_id, user_id)

        if conversation is None:
            return None

        conversation.title = title
        return conversation

    async def list_all(self, user_id: str):
        return [
            conversation
            for conversation in self.conversations.values()
            if conversation.user_id == user_id
        ]

    async def list_page(
        self,
        limit: int,
        offset: int,
        user_id: str,
    ):
        conversations = await self.list_all(user_id)

        conversations = sorted(
            conversations,
            key=lambda conversation: (
                conversation.created_at,
                conversation.id,
            ),
            reverse=True,
        )

        return conversations[offset : offset + limit]

    async def delete(
        self,
        conversation_id: str,
        user_id: str,
    ) -> bool:
        conversation = await self.get(conversation_id, user_id)

        if conversation is None:
            return False

        del self.conversations[conversation_id]
        return True


class FakeMessageRepository:
    def __init__(self):
        self.messages = []

    async def save(self, message):
        self.messages.append(message)

    async def list_for_conversation(self, conversation_id):
        return [
            message
            for message in self.messages
            if message.conversation_id == conversation_id
        ]


fake_repository = FakeConversationRepository()
fake_message_repository = FakeMessageRepository()


test_conversation = create_conversation(
    "Test conversation",
    user_id=TEST_USER_ID,
)
test_conversation.id = "test-session"

fake_repository.conversations[
    test_conversation.id
] = test_conversation


def override_get_agent():
    return FakeAgent()


def override_get_registered_user_id():
    return TEST_USER_ID


def override_get_conversation_repository():
    return fake_repository


def override_get_message_repository():
    return fake_message_repository


app.dependency_overrides[
    get_agent
] = override_get_agent

app.dependency_overrides[
    get_registered_user_id
] = override_get_registered_user_id

app.dependency_overrides[
    get_conversation_repository
] = override_get_conversation_repository

app.dependency_overrides[
    get_message_repository
] = override_get_message_repository


def test_health():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "AgentForge",
    }


def test_ready():
    connection = MagicMock()
    connection.execute = AsyncMock()

    connection_context = MagicMock()
    connection_context.__aenter__ = AsyncMock(return_value=connection)
    connection_context.__aexit__ = AsyncMock(return_value=None)

    with patch("app.api.database.pool.connection", return_value=connection_context):
        client = TestClient(app)
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "AgentForge",
    }
    connection.execute.assert_awaited_once_with("SELECT 1")


def test_ready_returns_503_when_database_unavailable():
    connection_context = MagicMock()
    connection_context.__aenter__ = AsyncMock(
        side_effect=ConnectionError("Database unavailable")
    )
    connection_context.__aexit__ = AsyncMock(return_value=None)

    with patch("app.api.database.pool.connection", return_value=connection_context):
        client = TestClient(app)
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "AgentForge database is not ready.",
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
        "response": "Test response: Hello AgentForge",
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

    stored_conversation = fake_repository.conversations[data["id"]]
    assert stored_conversation.user_id == TEST_USER_ID


def test_get_conversation():
    client = TestClient(app)

    response = client.get("/conversations/test-session")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == "test-session"
    assert data["title"] == test_conversation.title
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

    response = client.get("/conversations")

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
        "Conversation to delete",
        user_id=TEST_USER_ID,
    )

    fake_repository.conversations[
        conversation.id
    ] = conversation

    response = client.delete(
        f"/conversations/{conversation.id}"
    )

    assert response.status_code == 204

    assert conversation.id not in fake_repository.conversations


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
    assert len(fake_message_repository.messages) == 2

    user_message = fake_message_repository.messages[0]
    assistant_message = fake_message_repository.messages[1]

    assert user_message.role == "user"
    assert user_message.content == "Who is Alice?"
    assert user_message.conversation_id == "test-session"

    assert assistant_message.role == "assistant"
    assert (
        assistant_message.content
        == "Test response: Who is Alice?"
    )
    assert assistant_message.conversation_id == "test-session"


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
    assert data["messages"][0]["content"] == "Who is Alice?"

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
    assert response.text == "Hello from AgentForge"

    assert len(fake_message_repository.messages) == 2

    assert fake_message_repository.messages[0].content == "Hello"
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

    stored_conversation = fake_repository.conversations[
        "test-session"
    ]

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


def test_list_conversations_respects_limit():
    client = TestClient(app)

    response = client.get(
        "/conversations?limit=1&offset=0"
    )

    assert response.status_code == 200
    assert len(response.json()) <= 1


def test_list_conversations_respects_offset():
    client = TestClient(app)

    first_page = client.get(
        "/conversations?limit=1&offset=0"
    )
    second_page = client.get(
        "/conversations?limit=1&offset=1"
    )

    assert first_page.status_code == 200
    assert second_page.status_code == 200

    first_ids = {
        conversation["id"]
        for conversation in first_page.json()
    }
    second_ids = {
        conversation["id"]
        for conversation in second_page.json()
    }

    assert first_ids.isdisjoint(second_ids)


def test_list_conversations_rejects_invalid_limit():
    client = TestClient(app)

    for limit in (0, -1, 101):
        response = client.get(
            f"/conversations?limit={limit}"
        )

        assert response.status_code == 422


def test_list_conversations_rejects_negative_offset():
    client = TestClient(app)

    response = client.get(
        "/conversations?offset=-1"
    )

    assert response.status_code == 422


def test_other_user_cannot_access_conversation():
    client = TestClient(app)

    other_conversation = create_conversation(
        "Another user's private conversation",
        user_id=OTHER_USER_ID,
    )
    other_conversation.id = "other-user-session"

    fake_repository.conversations[
        other_conversation.id
    ] = other_conversation

    try:
        response = client.get(
            f"/conversations/{other_conversation.id}"
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Conversation not found.",
        }
    finally:
        fake_repository.conversations.pop(
            other_conversation.id,
            None,
        )


def test_list_conversations_excludes_other_users():
    client = TestClient(app)

    other_conversation = create_conversation(
        "Another user's private conversation",
        user_id=OTHER_USER_ID,
    )
    other_conversation.id = "other-user-list-session"

    fake_repository.conversations[
        other_conversation.id
    ] = other_conversation

    try:
        response = client.get(
            "/conversations",
            params={
                "limit": 100,
                "offset": 0,
            },
        )

        assert response.status_code == 200

        returned_ids = {
            conversation["id"]
            for conversation in response.json()
        }

        assert other_conversation.id not in returned_ids
        assert "test-session" in returned_ids

    finally:
        fake_repository.conversations.pop(
            other_conversation.id,
            None,
        )

def test_other_user_cannot_rename_conversation():
    client = TestClient(app)

    other_conversation = create_conversation(
        "Private conversation",
        user_id=OTHER_USER_ID,
    )
    other_conversation.id = "other-user-rename-session"

    fake_repository.conversations[
        other_conversation.id
    ] = other_conversation

    try:
        response = client.patch(
            f"/conversations/{other_conversation.id}",
            json={"title": "Unauthorized change"},
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Conversation not found.",
        }

        assert other_conversation.title == "Private conversation"

    finally:
        fake_repository.conversations.pop(
            other_conversation.id,
            None,
        )

def test_other_user_cannot_delete_conversation():
    client = TestClient(app)

    other_conversation = create_conversation(
        "Private conversation",
        user_id=OTHER_USER_ID,
    )
    other_conversation.id = "other-user-delete-session"

    fake_repository.conversations[
        other_conversation.id
    ] = other_conversation

    try:
        response = client.delete(
            f"/conversations/{other_conversation.id}"
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Conversation not found.",
        }

        assert (
            other_conversation.id
            in fake_repository.conversations
        )

    finally:
        fake_repository.conversations.pop(
            other_conversation.id,
            None,
        )
def test_other_user_cannot_read_conversation_messages():
    client = TestClient(app)

    other_conversation = create_conversation(
        "Private conversation",
        user_id=OTHER_USER_ID,
    )
    other_conversation.id = "other-user-messages-session"

    fake_repository.conversations[
        other_conversation.id
    ] = other_conversation

    try:
        response = client.get(
            f"/conversations/{other_conversation.id}/messages"
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Conversation not found.",
        }

    finally:
        fake_repository.conversations.pop(
            other_conversation.id,
            None,
        )

def test_other_user_cannot_chat_in_conversation():
    client = TestClient(app)

    other_conversation = create_conversation(
        "Private conversation",
        user_id=OTHER_USER_ID,
    )
    other_conversation.id = "other-user-chat-session"

    fake_repository.conversations[
        other_conversation.id
    ] = other_conversation

    fake_message_repository.messages.clear()

    try:
        response = client.post(
            "/chat",
            json={
                "message": "This should be rejected",
                "session_id": other_conversation.id,
            },
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Conversation not found.",
        }

        assert fake_message_repository.messages == []

    finally:
        fake_repository.conversations.pop(
            other_conversation.id,
            None,
        )

def test_other_user_cannot_stream_chat_in_conversation():
    client = TestClient(app)

    other_conversation = create_conversation(
        "Private conversation",
        user_id=OTHER_USER_ID,
    )
    other_conversation.id = "other-user-stream-session"

    fake_repository.conversations[
        other_conversation.id
    ] = other_conversation

    fake_message_repository.messages.clear()

    try:
        response = client.post(
            "/chat/stream",
            json={
                "message": "This should be rejected",
                "session_id": other_conversation.id,
            },
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Conversation not found.",
        }

        assert fake_message_repository.messages == []

    finally:
        fake_repository.conversations.pop(
            other_conversation.id,
            None,
        )

def test_other_user_cannot_stream_chat_events_in_conversation():
    client = TestClient(app)

    other_conversation = create_conversation(
        "Private conversation",
        user_id=OTHER_USER_ID,
    )
    other_conversation.id = "other-user-events-session"

    fake_repository.conversations[
        other_conversation.id
    ] = other_conversation

    fake_message_repository.messages.clear()

    try:
        response = client.post(
            "/chat/events",
            json={
                "message": "This should be rejected",
                "session_id": other_conversation.id,
            },
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Conversation not found.",
        }

        assert fake_message_repository.messages == []

    finally:
        fake_repository.conversations.pop(
            other_conversation.id,
            None,
        )

def test_list_conversations_requires_authentication():
    saved_override = app.dependency_overrides.pop(
        get_registered_user_id
    )

    try:
        client = TestClient(app)

        response = client.get("/conversations")

        assert response.status_code == 401

    finally:
        app.dependency_overrides[
            get_registered_user_id
        ] = saved_override

def test_list_conversations_rejects_invalid_token():
    saved_override = app.dependency_overrides.pop(
        get_registered_user_id
    )

    try:
        client = TestClient(app)

        response = client.get(
            "/conversations",
            headers={
                "Authorization": "Bearer invalid-token",
            },
        )

        assert response.status_code == 401

    finally:
        app.dependency_overrides[
            get_registered_user_id
        ] = saved_override
