from contextlib import asynccontextmanager
import logging
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from app.agents.mcp_agent import AgentForge
from app.logging_config import setup_logging


load_dotenv()
setup_logging()

logger = logging.getLogger(__name__)

agent = AgentForge()

def get_agent() -> AgentForge:
    return agent
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and stop AgentForge with the API."""

    logger.info("Starting AgentForge API")

    await agent.start()

    yield

    await agent.close()

    logger.info("AgentForge API stopped")


app = FastAPI(
    title="AgentForge API",
    description=(
        "AI agent API using LangGraph, RAG, "
        "local tools, and MCP."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Message to send to AgentForge.",
    )

    session_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Conversation session identifier.",
    )


class ChatResponse(BaseModel):
    response: str


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "AgentForge",
    }

@app.get("/ready")
async def ready(
    current_agent: AgentForge = Depends(get_agent),
):
    if current_agent.agent is None:
        raise HTTPException(
            status_code=503,
            detail="AgentForge is not ready.",
        )

    return {
        "status": "ready",
        "service": "AgentForge",
    }

@app.post(
    "/chat",
    response_model=ChatResponse,
)
async def chat(
    request: ChatRequest,
    current_agent: AgentForge = Depends(get_agent),
):    
    try:
        answer = await current_agent.ask(
            request.message,
            request.session_id,
        )
        return ChatResponse(
            response=answer,
        )

    except Exception:
        logger.exception(
            "Agent request failed"
        )

        raise HTTPException(
            status_code=500,
            detail="Agent request failed.",
        )
