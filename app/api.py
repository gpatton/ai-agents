from contextlib import asynccontextmanager
import logging
from app.database import Database
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.mcp_agent import AgentForge
from app.conversation_repository import ConversationRepository
from app.conversations import create_conversation
from app.logging_config import setup_logging
from app.message_repository import MessageRepository
from app.messages import create_message
from fastapi import Query  # Add Query to your existing FastAPI imports.

load_dotenv()
setup_logging()

logger = logging.getLogger(__name__)


agent = AgentForge()

database = Database()

conversation_repository = ConversationRepository(
    database.pool
)

message_repository = MessageRepository(
    database.pool
)

def get_agent() -> AgentForge:
    return agent


def get_conversation_repository() -> ConversationRepository:
    return conversation_repository


def get_message_repository() -> MessageRepository:
    return message_repository


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AgentForge API")

    await database.start()


    await agent.start()

    yield

    await agent.close()
    await database.close()

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

class RenameConversationRequest(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
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

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class ConversationMessagesResponse(BaseModel):
    conversation_id: str
    messages: list[MessageResponse]


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

@app.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    repository: ConversationRepository = Depends(
        get_conversation_repository
    ),
):
    conversations = await repository.list_page(
        limit=limit,
        offset=offset,
    )

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

@app.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
)
async def rename_conversation(
    conversation_id: str,
    request: RenameConversationRequest,
    repository: ConversationRepository = Depends(
        get_conversation_repository
    ),
):
    conversation = await repository.rename(
        conversation_id,
        request.title,
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

@app.get(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationMessagesResponse,
)
async def get_conversation_messages(
    conversation_id: str,
    repository: ConversationRepository = Depends(
        get_conversation_repository
    ),
    messages: MessageRepository = Depends(
        get_message_repository
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

    conversation_messages = (
        await messages.list_for_conversation(
            conversation_id
        )
    )

    return ConversationMessagesResponse(
        conversation_id=conversation_id,
        messages=[
            MessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at.isoformat(),
            )
            for message in conversation_messages
        ],
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
    messages: MessageRepository = Depends(
        get_message_repository
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

        user_message = create_message(
            conversation_id=request.session_id,
            role="user",
            content=request.message,
        )

        assistant_message = create_message(
            conversation_id=request.session_id,
            role="assistant",
            content=answer,
        )

        await messages.save(
            user_message
        )

        await messages.save(
            assistant_message
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

@app.post("/chat/stream")
async def stream_chat(
    request: ChatRequest,
    current_agent: AgentForge = Depends(get_agent),
    repository: ConversationRepository = Depends(
        get_conversation_repository
    ),
    messages: MessageRepository = Depends(
        get_message_repository
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

    async def generate():
        response_parts = []

        try:
            async for chunk in current_agent.stream(
                request.message,
                request.session_id,
            ):
                response_parts.append(chunk)
                yield chunk

            answer = "".join(response_parts)

            user_message = create_message(
                conversation_id=request.session_id,
                role="user",
                content=request.message,
            )

            assistant_message = create_message(
                conversation_id=request.session_id,
                role="assistant",
                content=answer,
            )

            await messages.save(
                user_message
            )

            await messages.save(
                assistant_message
            )

        except Exception:
            logger.exception(
                "Agent streaming request failed"
            )

    return StreamingResponse(
        generate(),
        media_type="text/plain",
    )

