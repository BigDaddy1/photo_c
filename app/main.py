from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import setup_routes
from app.db.session import engine
from app.error_handlers import unhandled_exception_handler


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(
    title="PhotoColor API",
    version="0.1.0",
    description="JPEG storage and five-colour palette analysis service",
    lifespan=lifespan,
)
app.add_exception_handler(Exception, unhandled_exception_handler)
setup_routes(app)
