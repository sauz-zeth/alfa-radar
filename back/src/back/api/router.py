from fastapi import APIRouter

from back.api.routes import (
    auth,
    businesses,
    feed,
    ingest,
    onboarding,
    profile,
    search,
    sources,
    tracked,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(businesses.router)
api_router.include_router(onboarding.router)
api_router.include_router(profile.router)
api_router.include_router(feed.router)
api_router.include_router(tracked.router)
api_router.include_router(sources.router)
api_router.include_router(search.router)
api_router.include_router(ingest.router)
