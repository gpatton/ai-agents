from psycopg import AsyncConnection

from app.config import settings
from app.messages import Message


class MessageRepository:
    """Store and retrieve AgentForge conversation messages."""

    async def setup(self) -> None:
        """Create the messages table if required."""

        async with await AsyncConnection.connect(
            settings.database_url
        ) as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    CONSTRAINT fk_conversation
                        FOREIGN KEY (conversation_id)
                        REFERENCES conversations(id)
                        ON DELETE CASCADE,
                    CONSTRAINT valid_message_role
                        CHECK (
                            role IN ('user', 'assistant')
                        )
                )
                """
            )

    async def save(
        self,
        message: Message,
    ) -> None:
        """Save a conversation message."""

        async with await AsyncConnection.connect(
            settings.database_url
        ) as connection:
            await connection.execute(
                """
                INSERT INTO messages (
                    id,
                    conversation_id,
                    role,
                    content,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    message.id,
                    message.conversation_id,
                    message.role,
                    message.content,
                    message.created_at,
                ),
            )

    async def list_for_conversation(
        self,
        conversation_id: str,
    ) -> list[Message]:
        """Return messages for a conversation."""

        async with await AsyncConnection.connect(
            settings.database_url
        ) as connection:
            cursor = await connection.execute(
                """
                SELECT
                    id,
                    conversation_id,
                    role,
                    content,
                    created_at
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC
                """,
                (conversation_id,),
            )

            rows = await cursor.fetchall()

        return [
            Message(
                id=row[0],
                conversation_id=row[1],
                role=row[2],
                content=row[3],
                created_at=row[4],
            )
            for row in rows
        ]
