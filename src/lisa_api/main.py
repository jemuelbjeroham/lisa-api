import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lisa.application import LISA
from lisa.conversation.redis import RedisConversationStore
from redis.asyncio import Redis

from lisa_api.logging import configure_logging
from lisa_api.routes import router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Starting LISA API")

    redis = Redis(
        host="localhost",
        port=6379,
        decode_responses=True,
    )

    try:
        await redis.ping()
        logger.info("Connected to Redis and it is active")

        conversation_store = RedisConversationStore(
            redis=redis,
        )

        async with LISA(
            conversation_store=conversation_store
        ) as lisa:
            app.state.lisa = lisa
            yield

    finally:
        await redis.aclose()
        logger.info("Connection to Redis has been closed")

    logger.info("LISA API shutdown complete")

app = FastAPI(
    title="LISA API",
    version="0.1.0",
    lifespan=lifespan
    )

# @app.middleware("http")
# async def debug_request(request, call_next):
#     print(
#         "DEBUG:",
#         request.method,
#         request.url,
#         request.headers.get("origin"),
#         request.headers.get("access-control-request-method"),
#     )

#     return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)