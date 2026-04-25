"""
Prometheus Metrics Configuration

Provides metrics for monitoring request latency, error rates, and processing times.
"""

from prometheus_client import Counter, Histogram, Gauge, Info, REGISTRY
from prometheus_client.exposition import generate_latest
from functools import wraps
import time
from typing import Callable


# ===================
# Application Info
# ===================
app_info = Info("iasw_app", "IASW Application Information")
app_info.info({
    "version": "1.0.0",
    "description": "Intelligent Account Servicing Workflow",
})

# ===================
# Request Metrics
# ===================
REQUEST_COUNT = Counter(
    "iasw_requests_total",
    "Total number of requests processed",
    ["endpoint", "method", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "iasw_request_latency_seconds",
    "Request latency in seconds",
    ["endpoint", "method"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ===================
# Document Processing Metrics
# ===================
DOCUMENT_PROCESSING_TIME = Histogram(
    "iasw_document_processing_seconds",
    "Document processing pipeline duration",
    ["change_type", "document_type", "status"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

PIPELINE_STAGE_TIME = Histogram(
    "iasw_pipeline_stage_seconds",
    "Time spent in each pipeline stage",
    ["stage"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

OCR_CONFIDENCE = Histogram(
    "iasw_ocr_confidence",
    "OCR confidence scores distribution",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0],
)

FORGERY_SCORE = Histogram(
    "iasw_forgery_score",
    "Forgery detection scores distribution",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

OVERALL_CONFIDENCE = Histogram(
    "iasw_overall_confidence",
    "Overall confidence scores distribution",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0],
)

# ===================
# Queue Metrics
# ===================
QUEUE_SIZE = Gauge(
    "iasw_review_queue_size",
    "Number of items in the review queue",
    ["risk_tier"],
)

QUEUE_WAIT_TIME = Histogram(
    "iasw_queue_wait_seconds",
    "Time requests spend waiting in queue",
    ["risk_tier"],
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400, 28800],
)

# ===================
# Decision Metrics
# ===================
DECISIONS_TOTAL = Counter(
    "iasw_decisions_total",
    "Total number of checker decisions",
    ["decision", "ai_recommendation", "risk_tier"],
)

AI_OVERRIDE_RATE = Counter(
    "iasw_ai_override_total",
    "Count of human decisions that override AI recommendation",
    ["ai_recommendation", "human_decision"],
)

# ===================
# Error Metrics
# ===================
ERRORS_TOTAL = Counter(
    "iasw_errors_total",
    "Total number of errors",
    ["error_type", "stage"],
)

# ===================
# LLM Metrics
# ===================
LLM_CALLS_TOTAL = Counter(
    "iasw_llm_calls_total",
    "Total LLM API calls",
    ["model", "purpose"],
)

LLM_LATENCY = Histogram(
    "iasw_llm_latency_seconds",
    "LLM API call latency",
    ["model", "purpose"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

LLM_TOKENS_USED = Counter(
    "iasw_llm_tokens_total",
    "Total LLM tokens used",
    ["model", "token_type"],
)


# ===================
# Helper Functions
# ===================
def track_request_time(endpoint: str, method: str):
    """Decorator to track request latency."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                status_code = getattr(result, "status_code", 200)
                REQUEST_COUNT.labels(
                    endpoint=endpoint,
                    method=method,
                    status_code=status_code,
                ).inc()
                return result
            except Exception as e:
                REQUEST_COUNT.labels(
                    endpoint=endpoint,
                    method=method,
                    status_code=500,
                ).inc()
                raise
            finally:
                REQUEST_LATENCY.labels(
                    endpoint=endpoint,
                    method=method,
                ).observe(time.time() - start_time)
        return wrapper
    return decorator


def track_pipeline_stage(stage: str):
    """Context manager to track pipeline stage timing."""
    class StageTimer:
        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            PIPELINE_STAGE_TIME.labels(stage=stage).observe(
                time.time() - self.start_time
            )
            if exc_type:
                ERRORS_TOTAL.labels(error_type=exc_type.__name__, stage=stage).inc()
            return False

    return StageTimer()


def record_document_metrics(
    change_type: str,
    document_type: str,
    status: str,
    processing_time: float,
    ocr_confidence: float = None,
    forgery_score: float = None,
    overall_confidence: float = None,
):
    """Record metrics for a completed document processing."""
    DOCUMENT_PROCESSING_TIME.labels(
        change_type=change_type,
        document_type=document_type,
        status=status,
    ).observe(processing_time)

    if ocr_confidence is not None:
        OCR_CONFIDENCE.observe(ocr_confidence)

    if forgery_score is not None:
        FORGERY_SCORE.observe(forgery_score)

    if overall_confidence is not None:
        OVERALL_CONFIDENCE.observe(overall_confidence)


def record_decision(
    decision: str,
    ai_recommendation: str,
    risk_tier: str,
):
    """Record a checker decision."""
    DECISIONS_TOTAL.labels(
        decision=decision,
        ai_recommendation=ai_recommendation,
        risk_tier=risk_tier,
    ).inc()

    # Track AI override
    if decision != ai_recommendation:
        AI_OVERRIDE_RATE.labels(
            ai_recommendation=ai_recommendation,
            human_decision=decision,
        ).inc()


def update_queue_metrics(queue_counts: dict[str, int]):
    """Update queue size metrics."""
    for risk_tier, count in queue_counts.items():
        QUEUE_SIZE.labels(risk_tier=risk_tier).set(count)


def get_metrics() -> bytes:
    """Generate Prometheus metrics output."""
    return generate_latest(REGISTRY)
