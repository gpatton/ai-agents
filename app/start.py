import logging

import uvicorn

from app.logging_config import setup_logging
from app.rag.vector_store import create_vector_store


logger = logging.getLogger(__name__)


def main():
    setup_logging()

    logger.info("Preparing AgentForge vector store")

    create_vector_store()

    logger.info("Vector store ready")

    uvicorn.run(
        "app.api:app",
        host="0.0.0.0",
        port=8000,
    )


if __name__ == "__main__":
    main()
