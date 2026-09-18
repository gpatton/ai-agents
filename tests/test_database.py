from app.database import Database


def test_database_creates_connection_pool():
    database = Database()

    assert database.pool is not None
    assert database.pool.min_size == 1
    assert database.pool.max_size == 10
