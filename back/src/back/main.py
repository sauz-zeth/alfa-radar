import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from back.api.router import api_router
from back.api.routes.health import router as health_router
from back.config import get_settings
from back.services.rss_poller import rss_poll_loop

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(rss_poll_loop()) if settings.rss_poll_enabled else None
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Бэкенд сервиса новостной аналитики: авторизация, онбординг бизнеса, "
        "персонализированная лента и отслеживаемые разборы."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(api_router, prefix=settings.api_prefix)

app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parent / "static"),
    name="static",
)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "openapi": "/openapi.json",
        "api_prefix": settings.api_prefix,
    }


def run() -> None:
    uvicorn.run("back.main:app", host="0.0.0.0", port=8000, reload=False)
