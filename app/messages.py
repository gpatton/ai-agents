import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Message:
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime


def create_message(
    conversation_id: str,
    role: str,
    content: str,
) -> Message:
    """Create conversation message metadata."""

    if role not in {"user", "assistant"}:
        raise ValueError(
            f"Invalid message role: {role}"
        )

    return Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role=role,
        content=content,
        created_at=datetime.now(timezone.utc),
    )
