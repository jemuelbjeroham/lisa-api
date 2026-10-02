import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from lisa.identity.models import User

from lisa_api.dependencies import get_current_user
from lisa_api.schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")

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
    