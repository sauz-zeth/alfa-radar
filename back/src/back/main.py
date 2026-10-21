import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from back.api.router import api_router
from back.api.routes.health import router as health_router
from back.config import get_settings

logging.basicConfig(level=logging.INFO)
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Бэкенд сервиса новостной аналитики: авторизация, онбординг бизнеса, "
        "персонализированная лента и отслеживаемые разборы."
    ),
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
