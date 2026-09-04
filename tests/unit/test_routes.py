from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lisa_api.routes import router


@pytest.mark.anyio
async def test_chat_route():
    lisa = Mock()

    lisa.graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                Mock(content="The firewall is blocking the connection.")
            ]
        }
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.lisa = lisa
        yield

    test_app = FastAPI(lifespan=lifespan)
    test_app.include_router(router)

    with TestClient(test_app) as client:
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "Why is the firewall blocking the connection?"
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "response": "The firewall is blocking the connection."
    }

    lisa.graph.ainvoke.assert_awaited_once()