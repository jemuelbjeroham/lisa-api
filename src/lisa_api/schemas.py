from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    conversation_id: UUID
    message: str

class ChatResponse(BaseModel):
    response: str