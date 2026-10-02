import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lisa.application import LISA
from lisa.conversation.redis import RedisConversationStore
from lisa.identity.development import DevelopmentIdentityProvider
from lisa.identity.models import User
from redis.asyncio import Redis

from lisa_api.logging import configure_logging
from lisa_api.routes import router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Starting LISA API")

    identity_provider = DevelopmentIdentityProvider(
        user=User(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            display_name="Local Dev User",
        )
    )
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
            app.state.identity_provider = identity_provider
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