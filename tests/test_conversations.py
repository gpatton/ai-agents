from datetime import timezone

from app.conversations import create_conversation


def test_create_conversation():
    conversation = create_conversation(
        "Employee questions"
    )

    assert conversation.title == "Employee questions"
    assert conversation.id
    assert conversation.created_at is not None


def test_conversation_id_is_unique():
    first = create_conversation()
    second = create_conversation()

    assert first.id != second.id


def test_created_at_uses_utc():
    conversation = create_conversation()

    assert conversation.created_at.tzinfo == timezone.utc
