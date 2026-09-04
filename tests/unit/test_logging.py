import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import Request

from lisa_api.logging import configure_logging
from lisa_api.routes import chat
from lisa_api.schemas import ChatRequest


def test_configure_logging_create_log_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    configure_logging()

    logger = logging.getLogger("test_logger")
    logger.info("Test log message")

    log_file = tmp_path / "logs" / "lisa-api.log"

    assert log_file.exists()
    assert "Test log message" in log_file.read_text()


@pytest.mark.anyio
async def test_chat_logs_request(caplog):
    graph = SimpleNamespace(
        ainvoke=AsyncMock(
            return_value={
                "messages": [
                    SimpleNamespace(content="Test response")
                ]
            }
        )
    )

    lisa = SimpleNamespace(graph=graph)

    app = SimpleNamespace(state=SimpleNamespace(lisa=lisa))

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/chat",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("testclient", 123),
        }
    )

    request.scope["app"] = app

    payload = ChatRequest(message="Test question")

    with caplog.at_level(logging.INFO):
        response = await chat(request, payload)

    assert response.response == "Test response"
    assert "Chat request received" in caplog.text
    assert "Chat request has been completed" in caplog.text