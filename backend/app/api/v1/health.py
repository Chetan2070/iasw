"""
Health Check Endpoints

Provides health and readiness checks for the application.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from app.db.session import get_db
from app.config import settings
from app.schemas.common import HealthResponse
from app.metrics import get_metrics

router = APIRouter()


@router.get("", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Check the health of the application and its dependencies.

    Returns status of:
    - Database connection
    - Redis connection
    """
    # Check database
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Check Redis
    redis_status = "healthy"
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"

    # Overall status
    overall_status = "healthy"
    if "unhealthy" in db_status or "unhealthy" in redis_status:
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        environment=settings.ENVIRONMENT,
        version="1.0.0",
        database=db_status,
        redis=redis_status
    )


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes-style readiness probe.

    Returns 200 if the application is ready to receive traffic.
    """
    return {"ready": True}


@router.get("/live")
async def liveness_check():
    """
    Kubernetes-style liveness probe.

    Returns 200 if the application is alive.
    """
    return {"alive": True}


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format for scraping.

    Metrics include:
    - Request counts and latency
    - Document processing times
    - OCR confidence scores
    - Forgery detection scores
    - Queue sizes
    - Decision counts
    - Error counts
    - LLM usage
    """
    return get_metrics()
