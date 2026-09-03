from contextlib import asynccontextmanager

from fastapi import FastAPI
from lisa.application import LISA


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with LISA() as lisa:
        app.state.lisa = lisa
        yield

app = FastAPI(
    title="LISA API",
    version="0.1.0",
    lifespan=lifespan
    )