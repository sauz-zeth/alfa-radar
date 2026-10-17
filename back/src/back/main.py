from fastapi import FastAPI

from back.api.router import api_router
from back.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
