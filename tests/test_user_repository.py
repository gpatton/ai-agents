import asyncio

import pytest

from app.user_repository import UserRepository


class FakeConnection:
    def __init__(self):
        self.calls = []

    async def execute(self, query, params):
        self.calls.append((query, params))


class FakePool:
    def __init__(self):
        self.connection_instance = FakeConnection()

    def connection(self):
        return self

    async def __aenter__(self):
        return self.connection_instance

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


def test_ensure_user_inserts_clerk_user():
    pool = FakePool()
    repository = UserRepository(pool)

    asyncio.run(repository.ensure_user("user_test_123"))

    assert len(pool.connection_instance.calls) == 1

    query, params = pool.connection_instance.calls[0]
    assert "ON CONFLICT (id) DO NOTHING" in query
    assert params == ("user_test_123",)


def test_ensure_user_rejects_invalid_id():
    pool = FakePool()
    repository = UserRepository(pool)

    with pytest.raises(ValueError):
        asyncio.run(repository.ensure_user(""))

    with pytest.raises(ValueError):
        asyncio.run(
            repository.ensure_user(
                "00000000-0000-4000-8000-000000000001"
            )
        )

    assert pool.connection_instance.calls == []
