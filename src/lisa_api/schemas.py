from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    conversation_id: UUID
    message: str
    enable_thinking: bool = False

class ChatResponse(BaseModel):
    response: str