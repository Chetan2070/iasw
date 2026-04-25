"""
Celery Tasks

Async tasks for document processing.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from celery import Task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.workers.celery_app import celery_app
from app.config import settings
from app.models import PendingRequest, AuditLog, RequestStatus, ActorType, EventType

logger = logging.getLogger(__name__)

# Create sync database session for Celery tasks
# (Celery doesn't play well with async by default)
sync_engine = create_engine(settings.DATABASE_SYNC_URL)
SyncSessionLocal = sessionmaker(bind=sync_engine)


class ProcessDocumentTask(Task):
    """
    Base task class for document processing.

    Provides common functionality for document processing tasks.
    """

    name = "process_document"
    max_retries = 3
    default_retry_delay = 60

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        request_id = args[0] if args else "unknown"
        logger.error(f"[{request_id}] Task failed: {exc}")

        # Update request status to FAILED
        try:
            with SyncSessionLocal() as session:
                request = session.query(PendingRequest).filter(
                    PendingRequest.request_id == request_id
                ).first()

                if request:
                    request.status = RequestStatus.FAILED

                    # Create audit log
                    audit = AuditLog.create(
                        request_id=request_id,
                        event_type=EventType.ERROR,
                        actor_type=ActorType.SYSTEM,
                        actor_id="celery_worker",
                        previous_state=request.status.value if request.status else None,
                        new_state=RequestStatus.FAILED.value,
                        action_details={
                            "error": str(exc),
                            "task_id": task_id,
                            "retries": self.request.retries,
                        },
                    )
                    session.add(audit)
                    session.commit()

        except Exception as e:
            logger.error(f"[{request_id}] Failed to update status on failure: {e}")

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        request_id = args[0] if args else "unknown"
        logger.info(f"[{request_id}] Task completed successfully")


@celery_app.task(bind=True, base=ProcessDocumentTask)
def process_document(self, request_id: str) -> Dict[str, Any]:
    """
    Process a document through the LangGraph pipeline.

    This task:
        1. Loads the request from the database
        2. Updates status to PROCESSING
        3. Runs the LangGraph pipeline
        4. Saves results back to the database
        5. Updates status to AI_VERIFIED_PENDING_HUMAN

    Args:
        request_id: The request ID to process

    Returns:
        Dict with processing results
    """
    logger.info(f"[{request_id}] Starting document processing task")

    with SyncSessionLocal() as session:
        # 1. Load request
        request = session.query(PendingRequest).filter(
            PendingRequest.request_id == request_id
        ).first()

        if not request:
            logger.error(f"[{request_id}] Request not found")
            return {"status": "error", "message": "Request not found"}

        # Check if already processed
        if request.status not in [RequestStatus.VALIDATED, RequestStatus.QUEUED]:
            logger.info(f"[{request_id}] Request already processed, skipping")
            return {"status": "skipped", "message": "Already processed"}

        # 2. Update status to PROCESSING
        previous_status = request.status.value
        request.status = RequestStatus.PROCESSING
        request.processing_started_at = datetime.utcnow()

        audit = AuditLog.create(
            request_id=request_id,
            event_type=EventType.STATE_CHANGE,
            actor_type=ActorType.SYSTEM,
            actor_id="celery_worker",
            agent_name="document_processor",
            previous_state=previous_status,
            new_state=RequestStatus.PROCESSING.value,
            action_details={"action": "start_processing", "task_id": self.request.id},
        )
        session.add(audit)
        session.commit()

        # 3. Run LangGraph pipeline
        try:
            # Import here to avoid circular imports
            from app.agents.graph import pipeline

            # Run async pipeline in sync context
            final_state = asyncio.run(
                pipeline.process(
                    request_id=request.request_id,
                    customer_id=request.customer_id,
                    change_type=request.change_type.value,
                    document_type=request.document_type.value,
                    requested_old_value=request.requested_old_value,
                    requested_new_value=request.requested_new_value,
                    document_path=request.document_storage_path,
                )
            )

            # 4. Save results to database
            request.ocr_confidence = final_state.get('ocr_confidence')
            request.extraction_confidence = final_state.get('extraction_confidence')
            request.extracted_old_value = final_state.get('extracted_old_value')
            request.extracted_new_value = final_state.get('extracted_new_value')
            request.extraction_metadata = final_state.get('extracted_fields')

            request.old_name_match_score = final_state.get('old_name_match_score')
            request.new_name_match_score = final_state.get('new_name_match_score')
            request.overall_confidence = final_state.get('overall_score')

            request.forgery_score = final_state.get('forgery_score')
            request.forgery_details = final_state.get('forgery_details')
            request.doc_authenticity_score = final_state.get('forgery_score')

            # Convert string values to enums
            from app.models.enums import RiskTier, ForgeryResult, Recommendation

            forgery_result_str = final_state.get('forgery_result')
            if forgery_result_str:
                try:
                    request.forgery_result = ForgeryResult(forgery_result_str)
                except ValueError:
                    request.forgery_result = None

            risk_tier_str = final_state.get('risk_tier')
            if risk_tier_str:
                try:
                    request.risk_tier = RiskTier(risk_tier_str)
                except ValueError:
                    request.risk_tier = None

            ai_recommendation_str = final_state.get('ai_recommendation')
            if ai_recommendation_str:
                try:
                    request.ai_recommendation = Recommendation(ai_recommendation_str)
                except ValueError:
                    request.ai_recommendation = None

            request.flags = final_state.get('flags', [])
            request.ai_summary = final_state.get('ai_summary')

            # 5. Update status
            request.status = RequestStatus.AI_VERIFIED_PENDING_HUMAN
            request.processing_completed_at = datetime.utcnow()
            request.staged_at = datetime.utcnow()

            # Create FileNet staging ID (mock)
            request.filenet_staging_id = f"FN-STG-{request_id}"

            # Create audit log
            audit = AuditLog.create(
                request_id=request_id,
                event_type=EventType.STATE_CHANGE,
                actor_type=ActorType.AI_AGENT,
                actor_id="document_processor",
                agent_name="langgraph_pipeline",
                agent_version="1.0.0",
                llm_model=settings.LLM_MODEL,
                previous_state=RequestStatus.PROCESSING.value,
                new_state=RequestStatus.AI_VERIFIED_PENDING_HUMAN.value,
                action_details={
                    "action": "processing_complete",
                    "overall_score": final_state.get('overall_score'),
                    "risk_tier": final_state.get('risk_tier'),
                    "ai_recommendation": final_state.get('ai_recommendation'),
                    "flags": final_state.get('flags', []),
                    "llm_calls": final_state.get('llm_calls', []),
                },
                record_snapshot=request.to_dict(),
            )
            session.add(audit)
            session.commit()

            logger.info(
                f"[{request_id}] Processing complete - "
                f"score: {final_state.get('overall_score'):.2f}, "
                f"recommendation: {final_state.get('ai_recommendation')}"
            )

            return {
                "status": "success",
                "request_id": request_id,
                "overall_score": final_state.get('overall_score'),
                "ai_recommendation": final_state.get('ai_recommendation'),
                "risk_tier": final_state.get('risk_tier'),
            }

        except Exception as e:
            logger.error(f"[{request_id}] Processing error: {str(e)}")

            # Check if we've exceeded max retries - if so, mark as FAILED
            if self.request.retries >= self.max_retries:
                logger.error(f"[{request_id}] Max retries exceeded, marking as FAILED")
                request.status = RequestStatus.FAILED

                audit = AuditLog.create(
                    request_id=request_id,
                    event_type=EventType.ERROR,
                    actor_type=ActorType.SYSTEM,
                    actor_id="celery_worker",
                    previous_state=RequestStatus.PROCESSING.value,
                    new_state=RequestStatus.FAILED.value,
                    action_details={
                        "error": str(e),
                        "retries": self.request.retries,
                    },
                )
                session.add(audit)
                session.commit()

                return {
                    "status": "failed",
                    "request_id": request_id,
                    "error": str(e),
                }

            # Retry the task
            raise self.retry(exc=e)


@celery_app.task
def cleanup_expired_locks():
    """
    Background task to release expired checker locks.

    Runs periodically to ensure requests with expired locks
    are returned to the queue.
    """
    logger.info("Running expired lock cleanup")

    with SyncSessionLocal() as session:
        now = datetime.utcnow()

        # Find requests with expired locks
        expired_requests = session.query(PendingRequest).filter(
            PendingRequest.status == RequestStatus.IN_REVIEW,
            PendingRequest.checker_lock_until < now,
        ).all()

        released_count = 0
        for request in expired_requests:
            previous_checker = request.assigned_checker

            request.status = RequestStatus.AI_VERIFIED_PENDING_HUMAN
            request.assigned_checker = None
            request.checker_lock_until = None

            audit = AuditLog.create(
                request_id=request.request_id,
                event_type=EventType.SYSTEM_EVENT,
                actor_type=ActorType.SYSTEM,
                actor_id="lock_cleanup",
                previous_state=RequestStatus.IN_REVIEW.value,
                new_state=RequestStatus.AI_VERIFIED_PENDING_HUMAN.value,
                action_details={
                    "action": "expired_lock_release",
                    "previous_checker": previous_checker,
                },
            )
            session.add(audit)
            released_count += 1

        session.commit()

        if released_count > 0:
            logger.info(f"Released {released_count} expired locks")

        return {"released": released_count}
