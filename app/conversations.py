import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

DEVELOPMENT_USER_ID = "00000000-0000-4000-8000-000000000001"
@dataclass
class Conversation:
    id: str
    title: str
    created_at: datetime
    user_id: str = DEVELOPMENT_USER_ID


def create_conversation(
    title: str = "New conversation",
    user_id: str = DEVELOPMENT_USER_ID,
) -> Conversation:
    """Create conversation metadata."""

    return Conversation(
        id=str(uuid.uuid4()),
        title=title,
        created_at=datetime.now(timezone.utc),
        user_id=user_id,
    )
