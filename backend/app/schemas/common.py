"""
Common Schemas

Shared schemas used across the application.
"""

from typing import Optional, List, Any
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Detail of a single error."""

    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    message: str
    details: Optional[List[ErrorDetail]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "error": "validation_failed",
                "message": "Request validation failed",
                "details": [
                    {"field": "customer_id", "message": "Customer not found in RPS"}
                ]
            }
        }


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = True
    message: str
    data: Optional[Any] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    environment: str
    version: str = "1.0.0"
    database: str = "unknown"
    redis: str = "unknown"
