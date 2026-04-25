"""
Structured Logging Configuration

Configures structlog for machine-parseable JSON logging with request context.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from app.config import settings


def add_app_context(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add application-level context to all log entries."""
    event_dict["app"] = settings.APP_NAME
    event_dict["environment"] = settings.ENVIRONMENT
    return event_dict


def setup_logging() -> None:
    """
    Configure structured logging for the application.

    In development: Human-readable colored output
    In production: JSON output for log aggregation (ELK, Splunk, etc.)
    """
    # Determine if we're in development or production
    is_development = settings.ENVIRONMENT == "development" or settings.DEBUG

    # Shared processors for all environments
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
        add_app_context,
    ]

    if is_development:
        # Development: colored, human-readable output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Production: JSON output for log aggregation
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure standard library logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    # Reduce noise from third-party libraries
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Usage:
        from app.logging_config import get_logger
        logger = get_logger(__name__)

        # Basic logging
        logger.info("processing_started", request_id="123")

        # With context binding
        log = logger.bind(request_id="123", customer_id="CUST-001")
        log.info("validation_passed")
        log.info("ocr_complete", confidence=0.95)

    Args:
        name: Logger name (typically __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


def bind_request_context(request_id: str, **kwargs) -> None:
    """
    Bind request context to all subsequent log calls in this context.

    Usage:
        bind_request_context(request_id="123", customer_id="CUST-001")
        logger.info("processing")  # Will include request_id and customer_id

    Args:
        request_id: The request ID to bind
        **kwargs: Additional context to bind
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id, **kwargs)


def clear_request_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()
