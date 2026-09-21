from psycopg_pool import AsyncConnectionPool


class UserRepository:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def ensure_user(self, user_id: str) -> None:
        """Create a local user record if this Clerk user is not registered."""
        if not user_id or not user_id.startswith("user_"):
            raise ValueError("Expected a Clerk user ID.")

        async with self.pool.connection() as connection:
            await connection.execute(
                """
                INSERT INTO users (id, email, password_hash, created_at)
                VALUES (%s, NULL, NULL, NOW())
                ON CONFLICT (id) DO NOTHING
                """,
                (user_id,),
            )
