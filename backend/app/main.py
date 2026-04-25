"""
FastAPI Application Entry Point

Main application factory and startup configuration.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.db.session import init_db
from app.logging_config import setup_logging, get_logger

# Initialize structured logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(
        "application_starting",
        app_name=settings.APP_NAME,
        version="1.0.0",
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
    )

    # Initialize database
    await init_db()
    logger.info("database_initialized")

    # Create storage directories
    import os
    os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    os.makedirs(f"{settings.STORAGE_PATH}/uploads", exist_ok=True)
    os.makedirs(f"{settings.STORAGE_PATH}/staging", exist_ok=True)
    os.makedirs(f"{settings.STORAGE_PATH}/approved", exist_ok=True)
    os.makedirs(f"{settings.STORAGE_PATH}/rejected", exist_ok=True)
    logger.info("storage_initialized", path=settings.STORAGE_PATH)

    yield

    # Shutdown
    logger.info("application_shutting_down")


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
