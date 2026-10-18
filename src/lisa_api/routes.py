
import json
import logging
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from lisa.identity.models import User
from pydantic import BaseModel, Field

from lisa_api.admin import router as admin_router
from lisa_api.auth import router as auth_router
from lisa_api.dependencies import get_current_user
from lisa_api.passwords import router as passwords_router
from lisa_api.schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(passwords_router)


class ConversationListResponse(BaseModel):
    conversations: list[UUID]

class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ConversationDetailResponse(BaseModel):
    id: UUID
    messages: list[ConversationMessage]

class RenameConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)

class ConversationActionResponse(BaseModel):
    message: str


def _message_content_to_text(content: object) -> str:
    """Convert LangChain message content into displayable text."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []

        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)

        return "\n".join(parts)

    return ""


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    payload: ChatRequest,
    user: Annotated[User, Depends(get_current_user)],
) -> ChatResponse:
    logger.info("Chat request received")

    lisa = request.app.state.lisa

    try:
        response = await lisa.chat(
            conversation_id=payload.conversation_id,
            message=payload.message,
            enable_thinking=payload.enable_thinking,
            user_id=user.id,
        )
    except Exception:
        logger.exception("Chat Request Failure")
        raise

    logger.info("Chat request has been completed")
    return ChatResponse(response=response)


@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    payload: ChatRequest,
    user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    logger.info("Streaming Chat Request Received")

    lisa = request.app.state.lisa

    async def generate():
        try:
            async for event in lisa.stream_chat(
                conversation_id=payload.conversation_id,
                message=payload.message,
                enable_thinking=payload.enable_thinking,
                user_id=user.id,
            ):
                yield json.dumps(event.model_dump()) + "\n"
        except Exception:
            logger.exception("Streaming Chat Request Failed")
            raise

    return StreamingResponse(generate(), media_type="text/plain")


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
)
async def list_conversations(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
) -> ConversationListResponse:
    lisa = request.app.state.lisa

    conversation_ids = await lisa.list_conversations(user_id=user.id)

    return ConversationListResponse(conversations=conversation_ids)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
async def get_conversation(
    conversation_id: UUID,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
) -> ConversationDetailResponse:
    lisa = request.app.state.lisa

    state = await lisa.conversation_store.get(
        user.id,
        conversation_id,
    )

    if state is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    messages: list[ConversationMessage] = []

    for message in state.get("messages", []):
        if message.type == "human":
            role = "user"
        elif message.type == "ai":
            role = "assistant"
        else:
            # Internal tool and system messages are not chat bubbles.
            continue

        content = _message_content_to_text(message.content)

        # Avoid rendering empty assistant messages, such as tool calls.
        if not content.strip():
            continue

        messages.append(
            ConversationMessage(
                role=role,
                content=content,
            )
        )

    return ConversationDetailResponse(
        id=conversation_id,
        messages=messages,
    )


@router.patch("/conversations/{conversation_id}")
async def rename_conversation(
    conversation_id: UUID,
    payload: RenameConversationRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
) -> ConversationActionResponse:
    lisa = request.app.state.lisa
    store = lisa.conversation_store

    # Verify ownership/existence before modifying metadata.
    state = await store.get(user.id, conversation_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    title = payload.title.strip()
    if not title:
        raise HTTPException(
            status_code=422,
            detail="Title cannot be empty",
        )

    await store.set_title(user.id, conversation_id, title)

    return ConversationActionResponse(
        message="Conversation renamed successfully"
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
) -> ConversationActionResponse:
    lisa = request.app.state.lisa
    store = lisa.conversation_store

    # Verify ownership/existence before deleting.
    state = await store.get(user.id, conversation_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    await store.delete(user.id, conversation_id)

    return ConversationActionResponse(
        message="Conversation deleted successfully"
    )
