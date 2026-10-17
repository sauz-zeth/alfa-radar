from fastapi import APIRouter

from back.api.routes import chains, companies, events, feed, health, swipes

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(feed.router)
api_router.include_router(events.router)
api_router.include_router(chains.router)
api_router.include_router(companies.router)
api_router.include_router(swipes.router)
