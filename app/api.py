from contextlib import asynccontextmanager
import logging

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.agents.mcp_agent import AgentForge
from app.conversation_repository import ConversationRepository
from app.conversations import create_conversation
from app.logging_config import setup_logging


load_dotenv()
setup_logging()

logger = logging.getLogger(__name__)

agent = AgentForge()
conversation_repository = ConversationRepository()


def get_agent() -> AgentForge:
    return agent


def get_conversation_repository() -> ConversationRepository:
    return conversation_repository


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AgentForge API")

    await conversation_repository.setup()
    await agent.start()

    yield

    await agent.close()

    logger.info("AgentForge API stopped")


app = FastAPI(
    title="AgentForge API",
    description=(
        "AI agent API using LangGraph, RAG, "
        "local tools, MCP, and persistent conversations."
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


class CreateConversationRequest(BaseModel):
    title: str = Field(
        default="New conversation",
        min_length=1,
        max_length=200,
    )


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str


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
    "/conversations",
    response_model=ConversationResponse,
    status_code=201,
)
async def create_conversation_endpoint(
    request: CreateConversationRequest,
    repository: ConversationRepository = Depends(
        get_conversation_repository
    ),
):
    conversation = create_conversation(
        request.title
    )

    await repository.save(
        conversation
    )

    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at.isoformat(),
    )


@app.get(
    "/conversations",
    response_model=list[ConversationResponse],
)
async def list_conversations(
    repository: ConversationRepository = Depends(
        get_conversation_repository
    ),
):
    conversations = await repository.list_all()

    return [
        ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at.isoformat(),
        )
        for conversation in conversations
    ]


@app.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
)
async def get_conversation(
    conversation_id: str,
    repository: ConversationRepository = Depends(
        get_conversation_repository
    ),
):
    conversation = await repository.get(
        conversation_id
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at.isoformat(),
    )


@app.post(
    "/chat",
    response_model=ChatResponse,
)
async def chat(
    request: ChatRequest,
    current_agent: AgentForge = Depends(get_agent),
    repository: ConversationRepository = Depends(
        get_conversation_repository
    ),
):
    conversation = await repository.get(
        request.session_id
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    try:
        answer = await current_agent.ask(
            request.message,
            request.session_id,
        )

        return ChatResponse(
            response=answer
        )

    except Exception:
        logger.exception(
            "Agent request failed"
        )

        raise HTTPException(
            status_code=500,
            detail="Agent request failed.",
        )

@app.delete(
    "/conversations/{conversation_id}",
    status_code=204,
)
async def delete_conversation(
    conversation_id: str,
    current_agent: AgentForge = Depends(get_agent),
    repository: ConversationRepository = Depends(
        get_conversation_repository
    ),
):
    conversation = await repository.get(
        conversation_id
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    try:
        await current_agent.delete_conversation(
            conversation_id
        )

        await repository.delete(
            conversation_id
        )

    except Exception:
        logger.exception(
            "Conversation deletion failed"
        )

        raise HTTPException(
            status_code=500,
            detail="Conversation deletion failed.",
        )
