
from psycopg_pool import AsyncConnectionPool

from app.conversations import Conversation


class ConversationRepository:
    """Store and retrieve AgentForge conversations."""

    def __init__(
        self,
        pool: AsyncConnectionPool,
    ):
        self.pool = pool


    async def list_page(
        self,
        limit: int,
        offset: int,
        user_id: str,
    ) -> list[Conversation]:
        """Return this user's conversations, newest first."""

        async with self.pool.connection() as connection:
            cursor = await connection.execute(
                """
                SELECT
                    id,
                    title,
                    created_at,
                    user_id
                FROM conversations
                WHERE user_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                OFFSET %s
                """,
                (user_id, limit, offset),
            )

            rows = await cursor.fetchall()

        return [
            Conversation(
                id=row[0],
                title=row[1],
                created_at=row[2],
                user_id=row[3],
            )
            for row in rows
        ]
    async def rename(
        self,
        conversation_id: str,
        title: str,
        user_id: str,
    ) -> Conversation | None:
        """Rename a conversation only if it belongs to this user."""

        async with self.pool.connection() as connection:
            cursor = await connection.execute(
                """
                UPDATE conversations
                SET title = %s
                WHERE id = %s
                  AND user_id = %s
                RETURNING id, title, created_at, user_id
                """,
                (title, conversation_id, user_id),
            )

            row = await cursor.fetchone()

        if row is None:
            return None

        return Conversation(
            id=row[0],
            title=row[1],
            created_at=row[2],
            user_id=row[3],
        )

    async def save(
        self,
        conversation: Conversation,
    ) -> None:
        """Save conversation metadata, including its owner."""

        async with self.pool.connection() as connection:
            await connection.execute(
                """
                INSERT INTO conversations (
                    id,
                    title,
                    created_at,
                    user_id
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    conversation.id,
                    conversation.title,
                    conversation.created_at,
                    conversation.user_id,
                ),
            )

    async def get(
        self,
        conversation_id: str,
        user_id: str,
    ) -> Conversation | None:
        """Retrieve a conversation only if it belongs to this user."""

        async with self.pool.connection() as connection:
            cursor = await connection.execute(
                """
                SELECT
                    id,
                    title,
                    created_at,
                    user_id
                FROM conversations
                WHERE id = %s
                  AND user_id = %s
                """,
                (conversation_id, user_id),
            )

            row = await cursor.fetchone()

        if row is None:
            return None

        return Conversation(
            id=row[0],
            title=row[1],
            created_at=row[2],
            user_id=row[3],
        )


    async def list_all(
        self,
        user_id: str,
    ) -> list[Conversation]:
        """Return only this user's conversations."""

        async with self.pool.connection() as connection:
            cursor = await connection.execute(
                """
                SELECT
                    id,
                    title,
                    created_at,
                    user_id
                FROM conversations
                WHERE user_id = %s
                ORDER BY created_at DESC, id DESC
                """,
                (user_id,),
            )

            rows = await cursor.fetchall()

        return [
            Conversation(
                id=row[0],
                title=row[1],
                created_at=row[2],
                user_id=row[3],
            )
            for row in rows
        ]

    async def delete(
        self,
        conversation_id: str,
        user_id: str,
    ) -> bool:
        """Delete a conversation only if it belongs to this user."""

        async with self.pool.connection() as connection:
            cursor = await connection.execute(
                """
                DELETE FROM conversations
                WHERE id = %s
                  AND user_id = %s
                """,
                (conversation_id, user_id),
            )

            return cursor.rowcount > 0
