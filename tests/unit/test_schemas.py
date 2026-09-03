from lisa_api.schemas import ChatRequest, ChatResponse


def test_chat_request():
    request = ChatRequest(message="Why is the firewall not responding?")

    assert request.message == "Why is the firewall not responding?"

def test_chat_response():
    response = ChatResponse(response="The reason is...")

    assert response.response == "The reason is..."