FROM python:3.14-slim-bookworm AS build

COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /workspace

COPY lisa-api/ ./lisa-api/
COPY LISA/ ./LISA/
COPY lisa-mcp-server/ ./lisa-mcp-server/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --project /workspace/lisa-api --locked --no-dev --no-editable

FROM python:3.14-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8008 \
    LISA_REDIS_URL=redis://redis:6379/0 \
    LISA_CORS_ALLOWED_ORIGINS="" \
    LISA_LOG_FILE="" \
    LISA_MCP_SERVER_COMMAND=/app/.venv/bin/python \
    LISA_MCP_SERVER_ARGS='["-m","lisa_mcp_server.server"]' \
    LISA_MCP_SERVER_CWD=/app \
    NET_TOOLS_API_URL=http://net-tools-app:8000

WORKDIR /app

RUN groupadd --system --gid 10001 lisa \
    && useradd --system --uid 10001 --gid lisa --home-dir /app --no-create-home lisa

COPY --from=build --chown=10001:10001 /app/.venv /app/.venv

USER 10001:10001

EXPOSE 8008

CMD ["sh", "-c", "exec uvicorn lisa_api.main:app --host 0.0.0.0 --port \"${PORT}\""]