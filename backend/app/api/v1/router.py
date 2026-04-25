"""
API v1 Router

Main router that includes all API endpoints.
"""

from fastapi import APIRouter

from app.api.v1 import requests, checker, health

api_router = APIRouter()

# Include sub-routers
api_router.include_router(
    requests.router,
    prefix="/requests",
    tags=["Requests"]
)

api_router.include_router(
    checker.router,
    prefix="/checker",
    tags=["Checker"]
)

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"]
)
