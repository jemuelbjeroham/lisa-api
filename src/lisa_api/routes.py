import logging

from fastapi import APIRouter, Request

from lisa_api.schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")

@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    logger.info("Chat request received")

    lisa = request.app.state.lisa

    try:
        response = await lisa.graph.ainvoke(
            conversation_id=str(payload.conversation_id),
            message=payload.message
        )

    except Exception:
        logger.exception("Chat Request Failure")
        raise

    logger.info("Chat request has been completed")

    return ChatResponse(response=response)
