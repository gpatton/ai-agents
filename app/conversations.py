import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Conversation:
    id: str
    title: str
    created_at: datetime


def create_conversation(
    title: str = "New conversation",
) -> Conversation:
    """Create conversation metadata."""

    return Conversation(
        id=str(uuid.uuid4()),
        title=title,
        created_at=datetime.now(timezone.utc),
    )
