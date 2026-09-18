import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv


# Load environment variables from .env before
# creating the application settings.
load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv(
        "APP_NAME",
        "AgentForge",
    )

    model_name: str = os.getenv(
        "MODEL_NAME",
        "gpt-5.4-mini",
    )

    chroma_dir: str = os.getenv(
        "CHROMA_DIR",
        "chroma_db",
    )

    mcp_server_command: str = os.getenv(
        "MCP_SERVER_COMMAND",
        sys.executable,
    )

    mcp_server_path: str = os.getenv(
        "MCP_SERVER_PATH",
        "app/mcp/server.py",
    )
    
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://agentforge:agentforge@localhost:5432/agentforge",
    )


settings = Settings()
