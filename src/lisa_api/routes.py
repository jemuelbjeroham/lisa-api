from fastapi import APIRouter, Request

from lisa_api.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1")

@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    lisa = request.app.state.lisa

    result = await lisa.graph.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": payload.message,
                }
            ]
        }
    )

    response = result["messages"][-1]

    return ChatResponse(response=response.content)
