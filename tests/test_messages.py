from datetime import timezone

import pytest

from app.messages import create_message


def test_create_user_message():
    message = create_message(
        conversation_id="conversation-1",
        role="user",
        content="Who is Alice?",
    )

    assert message.id
    assert message.conversation_id == "conversation-1"
    assert message.role == "user"
    assert message.content == "Who is Alice?"
    assert message.created_at.tzinfo == timezone.utc


def test_create_assistant_message():
    message = create_message(
        conversation_id="conversation-1",
        role="assistant",
        content="Alice is an AI Engineer.",
    )

    assert message.role == "assistant"


def test_message_ids_are_unique():
    first = create_message(
        "conversation-1",
        "user",
        "First message",
    )

    second = create_message(
        "conversation-1",
        "user",
        "Second message",
    )

    assert first.id != second.id


def test_invalid_role_is_rejected():
    with pytest.raises(ValueError):
        create_message(
            "conversation-1",
            "system",
            "Invalid message",
        )
