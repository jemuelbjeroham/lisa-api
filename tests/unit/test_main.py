from unittest.mock import AsyncMock, Mock, patch

import pytest

from lisa_api.main import app


def test_app_is_created():
    assert app.title == "LISA API"
    assert app.version == "0.1.0"

@pytest.mark.anyio
async def test_lifespan_manages_lisa():
    mock_lisa = Mock()
    mock_lisa.__aenter__ = AsyncMock(return_value=mock_lisa)
    mock_lisa.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "lisa_api.main.LISA",
        return_value=mock_lisa,
    ) as lisa_class:
        async with app.router.lifespan_context(app):
            assert app.state.lisa is mock_lisa

        lisa_class.assert_called_once()
        mock_lisa.__aenter__.assert_awaited_once()
        mock_lisa.__aexit__.assert_awaited_once()
