import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from lisa.application import LISA

from lisa_api.logging import configure_logging
from lisa_api.routes import router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Starting LISA API")

    async with LISA() as lisa:
        app.state.lisa = lisa
        yield

    logger.info("LISA API shutdown complete")

app = FastAPI(
    title="LISA API",
    version="0.1.0",
    lifespan=lifespan
    )

app.include_router(router)