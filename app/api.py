from contextlib import asynccontextmanager
import logging
import json
from app.database import Database
from app.auth import get_current_user_id
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.user_repository import UserRepository
from app.agents.mcp_agent import AgentForge
from app.conversation_repository import ConversationRepository
from app.conversations import create_conversation
from app.logging_config import setup_logging
from app.message_repository import MessageRepository
from app.messages import create_message
from fastapi import Query  # Add Query to your existing FastAPI imports.
import asyncio
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
user_repository = UserRepository(database.pool)

def get_user_repository() -> UserRepository:
    return user_repository

async def get_registered_user_id(
    user_id: str = Depends(get_current_user_id),
    repository: UserRepository = Depends(get_user_repository),
) -> str:
    """Return the verified Clerk user ID after ensuring a local user exists."""
    await repository.ensure_user(user_id)
    return user_id

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
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
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

    try:
        async with database.pool.connection(timeout=3) as connection:
            await connection.execute("SELECT 1")
    except Exception:
        logger.exception("AgentForge readiness check: database unavailable")
        raise HTTPException(
            status_code=503,
            detail="AgentForge database is not ready.",
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
    user_id: str = Depends(get_registered_user_id),
):
    conversation = create_conversation(
        request.title,
        user_id=user_id,
    )

    await repository.save(conversation)

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
    user_id: str = Depends(get_registered_user_id),
):
    conversations = await repository.list_page(
        limit=limit,
        offset=offset,
        user_id=user_id,
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
    user_id: str = Depends(get_registered_user_id),
):
    conversation = await repository.get(
        conversation_id,
        user_id,
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
    user_id: str = Depends(get_registered_user_id),
):
    conversation = await repository.rename(
        conversation_id,
        request.title,
        user_id,
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
    user_id: str = Depends(get_registered_user_id),
):
    conversation = await repository.get(
        conversation_id,
        user_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    conversation_messages = await messages.list_for_conversation(
        conversation_id
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
    user_id: str = Depends(get_registered_user_id),
):
    conversation = await repository.get(
        conversation_id,
        user_id,
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

        deleted = await repository.delete(
            conversation_id,
            user_id,
        )

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

    except HTTPException:
        raise

    except Exception:
        logger.exception("Conversation deletion failed")

        raise HTTPException(
            status_code=500,
            detail="Conversation deletion failed.",
        ) from None

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
    user_id: str = Depends(get_registered_user_id),
):
    conversation = await repository.get(
        request.session_id,
        user_id,
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

        await messages.save(user_message)
        await messages.save(assistant_message)

        return ChatResponse(response=answer)

    except Exception:
        logger.exception("Agent request failed")

        raise HTTPException(
            status_code=500,
            detail="Agent request failed.",
        ) from None
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
    user_id: str = Depends(get_registered_user_id),
):
    conversation = await repository.get(
        request.session_id,
        user_id,
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

            await messages.save(user_message)
            await messages.save(assistant_message)

        except asyncio.CancelledError:
            logger.info(
                "Agent streaming request cancelled | session_id=%s",
                request.session_id,
            )
            raise

        except Exception:
            logger.exception(
                "Agent streaming request failed"
            )
    return StreamingResponse(
        generate(),
        media_type="text/plain",
    )

@app.post("/chat/events")
async def stream_chat_events(
    request: ChatRequest,
    current_agent: AgentForge = Depends(get_agent),
    repository: ConversationRepository = Depends(
        get_conversation_repository
    ),
    messages: MessageRepository = Depends(
        get_message_repository
    ),
    user_id: str = Depends(get_registered_user_id),
):
    conversation = await repository.get(
        request.session_id,
        user_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    def encode_event(event: dict) -> str:
        return json.dumps(event, ensure_ascii=False) + "\n"

    async def generate():
        response_parts = []
        tool_events = asyncio.Queue()

        def on_tool_event(event: dict) -> None:
            tool_events.put_nowait(event)

        stream = current_agent.stream(
            request.message,
            request.session_id,
            on_tool_event=on_tool_event,
        )

        next_chunk = None

        try:
            next_chunk = asyncio.create_task(anext(stream))

            while True:
                next_tool_event = asyncio.create_task(
                    tool_events.get()
                )

                done, pending = await asyncio.wait(
                    {next_chunk, next_tool_event},
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if next_tool_event in done:
                    yield encode_event(
                        next_tool_event.result()
                    )

                if next_chunk in done:
                    try:
                        chunk = next_chunk.result()
                    except StopAsyncIteration:
                        if next_tool_event not in done:
                            next_tool_event.cancel()
                            await asyncio.gather(
                                next_tool_event,
                                return_exceptions=True,
                            )
                        break

                    response_parts.append(chunk)

                    yield encode_event(
                        {
                            "type": "text",
                            "content": chunk,
                        }
                    )

                    next_chunk = asyncio.create_task(
                        anext(stream)
                    )

                if next_tool_event not in done:
                    next_tool_event.cancel()
                    await asyncio.gather(
                        next_tool_event,
                        return_exceptions=True,
                    )

            while not tool_events.empty():
                yield encode_event(
                    tool_events.get_nowait()
                )

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

            await messages.save(user_message)
            await messages.save(assistant_message)

            yield encode_event(
                {
                    "type": "done",
                }
            )

        except asyncio.CancelledError:
            logger.info(
                "Agent event stream cancelled | session_id=%s",
                request.session_id,
            )
            raise

        except Exception:
            logger.exception(
                "Agent event stream failed"
            )

            yield encode_event(
                {
                    "type": "error",
                    "message": "Agent request failed.",
                }
            )

        finally:
            if next_chunk is not None and not next_chunk.done():
                next_chunk.cancel()
                await asyncio.gather(
                    next_chunk,
                    return_exceptions=True,
                )

            await stream.aclose()

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )
