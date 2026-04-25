"""
FastAPI Application Entry Point

Main application factory and startup configuration.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.api.v1.router import api_router
from app.db.session import init_db

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v1.0.0")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Create storage directories
    import os
    os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    os.makedirs(f"{settings.STORAGE_PATH}/uploads", exist_ok=True)
    os.makedirs(f"{settings.STORAGE_PATH}/staging", exist_ok=True)
    os.makedirs(f"{settings.STORAGE_PATH}/approved", exist_ok=True)
    os.makedirs(f"{settings.STORAGE_PATH}/rejected", exist_ok=True)
    logger.info(f"Storage directories created at {settings.STORAGE_PATH}")

    yield

    # Shutdown
    logger.info("Shutting down application")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title=settings.APP_NAME,
        description="Intelligent Account Servicing Workflow - AI-powered document verification with human-in-the-loop",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs" if settings.DEBUG else "disabled"
        }

    # Health check
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "environment": settings.ENVIRONMENT
        }

    return app


# Create application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
