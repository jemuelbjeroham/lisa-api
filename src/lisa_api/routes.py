import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from lisa.identity.models import User
from pydantic import BaseModel

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


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, payload: ChatRequest, user: Annotated[User, Depends(get_current_user)]) -> ChatResponse:
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
async def chat_stream(request: Request, payload: ChatRequest, user: Annotated[User, Depends(get_current_user)]) -> StreamingResponse:
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

@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
) -> ConversationListResponse:
    lisa = request.app.state.lisa

    conversation_ids = await lisa.list_conversations(user_id=user.id)

    return ConversationListResponse(conversations=conversation_ids)