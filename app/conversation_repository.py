from psycopg_pool import AsyncConnectionPool

from app.conversations import Conversation


class ConversationRepository:
    """Store and retrieve AgentForge conversations."""

    def __init__(
        self,
        pool: AsyncConnectionPool,
    ):
        self.pool = pool

    async def setup(self) -> None:
        """Create the conversations table if required."""

        async with self.pool.connection() as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                )
                """
            )

    async def save(
        self,
        conversation: Conversation,
    ) -> None:
        """Save conversation metadata."""

        async with self.pool.connection() as connection:
            await connection.execute(
                """
                INSERT INTO conversations (
                    id,
                    title,
                    created_at
                )
                VALUES (%s, %s, %s)
                """,
                (
                    conversation.id,
                    conversation.title,
                    conversation.created_at,
                ),
            )

    async def get(
        self,
        conversation_id: str,
    ) -> Conversation | None:
        """Retrieve a conversation by ID."""

        async with self.pool.connection() as connection:
            cursor = await connection.execute(
                """
                SELECT
                    id,
                    title,
                    created_at
                FROM conversations
                WHERE id = %s
                """,
                (conversation_id,),
            )

            row = await cursor.fetchone()

        if row is None:
            return None

        return Conversation(
            id=row[0],
            title=row[1],
            created_at=row[2],
        )

    async def list_all(
        self,
    ) -> list[Conversation]:
        """Return all conversations."""

        async with self.pool.connection() as connection:
            cursor = await connection.execute(
                """
                SELECT
                    id,
                    title,
                    created_at
                FROM conversations
                ORDER BY created_at DESC
                """
            )

            rows = await cursor.fetchall()

        return [
            Conversation(
                id=row[0],
                title=row[1],
                created_at=row[2],
            )
            for row in rows
        ]

    async def delete(
        self,
        conversation_id: str,
    ) -> bool:
        """Delete conversation metadata."""

        async with self.pool.connection() as connection:
            cursor = await connection.execute(
                """
                DELETE FROM conversations
                WHERE id = %s
                """,
                (conversation_id,),
            )

            return cursor.rowcount > 0
