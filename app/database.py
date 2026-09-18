from psycopg_pool import AsyncConnectionPool

from app.config import settings


class Database:
    """Manage the AgentForge PostgreSQL connection pool."""

    def __init__(self):
        self.pool = AsyncConnectionPool(
            conninfo=settings.database_url,
            min_size=1,
            max_size=10,
            open=False,
        )

    async def start(self) -> None:
        """Open the PostgreSQL connection pool."""

        await self.pool.open()
        await self.pool.wait()

    async def close(self) -> None:
        """Close the PostgreSQL connection pool."""

        await self.pool.close()
