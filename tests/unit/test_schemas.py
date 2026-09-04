from uuid import uuid4

from lisa_api.schemas import ChatRequest, ChatResponse


def test_chat_request():
    conversation_id = uuid4()
    request = ChatRequest(conversation_id=conversation_id, message="Why is the firewall not responding?")

    assert request.conversation_id == conversation_id
    assert request.message == "Why is the firewall not responding?"


def test_chat_response():
    response = ChatResponse(response="The reason is...")

    assert response.response == "The reason is..."