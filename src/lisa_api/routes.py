import logging

from fastapi import APIRouter, Request, status
from fastapi.responses import StreamingResponse

from lisa_api.schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")

@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    logger.info("Chat request received")

    lisa = request.app.state.lisa

    try:
        response = await lisa.chat(
            conversation_id=payload.conversation_id,
            message=payload.message
        )

    except Exception:
        logger.exception("Chat Request Failure")
        raise

    logger.info("Chat request has been completed")

    return ChatResponse(response=response)

@router.post("/chat/stream")
async def chat_stream(request: Request, payload:ChatRequest) -> StreamingResponse:
    logger.info("Streaming Chat Request Received")

    lisa = request.app.state.lisa

    async def generate():
        try:
            async for chunk in lisa.stream_chat(
                conversation_id=payload.conversation_id,
                message=payload.message,
            ):
                yield chunk

        except Exception:
            logger.exception("Streaming Chat Request Failed")
            raise

    return StreamingResponse(generate(), media_type="text/plain")
    