import logging

from alembic import command
from alembic.config import Config

import uvicorn

from app.logging_config import setup_logging
from app.rag.vector_store import (
    create_vector_store,
    vector_store_needs_indexing,
)


logger = logging.getLogger(__name__)
def run_database_migrations() -> None:
    """Upgrade the application database schema."""

    logger.info("Running database migrations")

    alembic_config = Config("alembic.ini")
    command.upgrade(alembic_config, "head")

    setup_logging()
    logger.info("Database migrations completed")

def main():
    setup_logging()

    logger.info("Checking AgentForge vector store")

    if vector_store_needs_indexing():
        logger.info(
            "Document index is missing or outdated; "
            "indexing documents"
        )
        create_vector_store()
        logger.info("Document indexing completed")
    else:
        logger.info(
            "Document index is current; skipping indexing"
        )

    logger.info("Vector store ready")

    run_database_migrations()

    uvicorn.run(
        "app.api:app",
        host="0.0.0.0",
        port=8000,
    )

if __name__ == "__main__":
    main()
