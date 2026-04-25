"""
Request Endpoints

API endpoints for staff intake operations.
"""

import os
import uuid
import hashlib
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.config import settings
from app.models import (
    PendingRequest, Customer, AuditLog,
    ChangeType, DocumentType, RequestStatus, ActorType, EventType,
    is_document_allowed
)
from app.schemas import (
    CreateRequestSchema, RequestResponse, RequestSummary,
    RequestDetail, UploadResponse, RequestFilters, PaginatedRequests,
    ErrorResponse, ConfidenceBreakdown, ForgeryDetail, ExtractionDetail
)

logger = logging.getLogger(__name__)

router = APIRouter()


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"REQ-{uuid.uuid4().hex[:8].upper()}"


def generate_idempotency_key(customer_id: str, change_type: str, file_hash: str = "") -> str:
    """Generate idempotency key for duplicate detection."""
    timestamp_minute = datetime.utcnow().strftime("%Y%m%d%H%M")
    data = f"{customer_id}:{change_type}:{timestamp_minute}:{file_hash}"
    return hashlib.sha256(data.encode()).hexdigest()[:64]


@router.post(
    "",
    response_model=RequestResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation failed"},
        409: {"model": ErrorResponse, "description": "Duplicate request"},
    }
)
async def create_request(
    data: CreateRequestSchema,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new change request.

    This endpoint performs synchronous validation (< 500ms) and returns
    a reference number immediately. The staff can then upload the
    supporting document.

    **Validation checks:**
    - Customer exists in RPS (core banking) by account number
    - Document type is allowed for the change type
    - No duplicate in-progress request

    **Note:** Document upload is a separate step via POST /requests/{id}/upload
    """
    logger.info(f"[INTAKE] Starting request creation for account: {data.account_number}")

    # 1. Check customer exists in RPS by account number
    logger.info(f"[INTAKE] Step 1: Looking up account {data.account_number} in RPS...")
    customer = await db.execute(
        select(Customer).where(Customer.account_number == data.account_number)
    )
    customer = customer.scalar_one_or_none()

    if not customer:
        logger.warning(f"[INTAKE] FAILED: Account {data.account_number} not found in RPS")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "account_not_found",
                "message": f"Account number {data.account_number} not found in RPS"
            }
        )

    logger.info(f"[INTAKE] SUCCESS: Account {data.account_number} found - Customer: {customer.full_name} (ID: {customer.customer_id})")

    # 2. Check document type is allowed for change type
    logger.info(f"[INTAKE] Step 2: Validating document type {data.document_type.value} for change type {data.change_type.value}...")
    if not is_document_allowed(data.change_type, data.document_type):
        logger.warning(f"[INTAKE] FAILED: Document type {data.document_type.value} not allowed for {data.change_type.value}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_document_type",
                "message": f"Document type {data.document_type.value} is not allowed for {data.change_type.value}"
            }
        )
    logger.info(f"[INTAKE] SUCCESS: Document type {data.document_type.value} is valid for {data.change_type.value}")

    # 3. Check for duplicate in-progress request
    logger.info(f"[INTAKE] Step 3: Checking for duplicate in-progress requests...")
    existing = await db.execute(
        select(PendingRequest).where(
            PendingRequest.customer_id == customer.customer_id,
            PendingRequest.change_type == data.change_type,
            PendingRequest.status.in_([
                RequestStatus.INTAKE_RECEIVED,
                RequestStatus.VALIDATED,
                RequestStatus.QUEUED,
                RequestStatus.PROCESSING,
                RequestStatus.AI_VERIFIED_PENDING_HUMAN,
                RequestStatus.IN_REVIEW,
                RequestStatus.PENDING_INFO,
            ])
        )
    )
    existing = existing.scalar_one_or_none()

    if existing:
        logger.warning(f"[INTAKE] FAILED: Duplicate request found - {existing.request_id}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "duplicate_request",
                "message": f"An active request already exists: {existing.request_id}"
            }
        )
    logger.info(f"[INTAKE] SUCCESS: No duplicate requests found")

    # 4. Generate IDs
    request_id = generate_request_id()
    idempotency_key = generate_idempotency_key(customer.customer_id, data.change_type.value)
    logger.info(f"[INTAKE] Step 4: Generated request ID: {request_id}")

    # 5. Create request record
    logger.info(f"[INTAKE] Step 5: Creating request record...")
    request = PendingRequest(
        request_id=request_id,
        idempotency_key=idempotency_key,
        customer_id=customer.customer_id,
        change_type=data.change_type,
        document_type=data.document_type,
        requested_old_value=data.current_value,
        requested_new_value=data.new_value,
        status=RequestStatus.INTAKE_RECEIVED,
        created_by="staff_user",  # TODO: Get from auth
        flags=[],
    )

    db.add(request)

    # 6. Create audit log
    logger.info(f"[INTAKE] Step 6: Creating audit log entry...")
    audit = AuditLog.create(
        request_id=request_id,
        event_type=EventType.STATE_CHANGE,
        actor_type=ActorType.HUMAN,
        actor_id="staff_user",
        previous_state=None,
        new_state=RequestStatus.INTAKE_RECEIVED.value,
        action_details={"action": "create_request", "data": data.model_dump()},
    )
    db.add(audit)

    await db.commit()
    logger.info(f"[INTAKE] SUCCESS: Request {request_id} created successfully for customer {customer.full_name}")

    return RequestResponse(
        request_id=request_id,
        status=RequestStatus.INTAKE_RECEIVED,
        message=f"Request created successfully for {customer.full_name}. Please upload supporting document.",
        customer_name=customer.full_name
    )


@router.post(
    "/{request_id}/upload",
    response_model=UploadResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file"},
        404: {"model": ErrorResponse, "description": "Request not found"},
    }
)
async def upload_document(
    request_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a supporting document for a request.

    **Validation checks:**
    - File format (PDF, JPEG, PNG, TIFF)
    - File size (max 10MB)
    - Request exists and is in correct status

    After successful upload, the request is queued for AI processing.
    """
    logger.info(f"[UPLOAD] Starting document upload for request: {request_id}")

    # 1. Check request exists
    logger.info(f"[UPLOAD] Step 1: Verifying request {request_id} exists...")
    request = await db.execute(
        select(PendingRequest).where(PendingRequest.request_id == request_id)
    )
    request = request.scalar_one_or_none()

    if not request:
        logger.warning(f"[UPLOAD] FAILED: Request {request_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "request_not_found", "message": f"Request {request_id} not found"}
        )
    logger.info(f"[UPLOAD] SUCCESS: Request {request_id} found")

    # 2. Check request is in correct status
    logger.info(f"[UPLOAD] Step 2: Checking request status (current: {request.status.value})...")
    if request.status != RequestStatus.INTAKE_RECEIVED:
        logger.warning(f"[UPLOAD] FAILED: Invalid status {request.status.value} for upload")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_status",
                "message": f"Cannot upload document for request in status {request.status.value}"
            }
        )
    logger.info(f"[UPLOAD] SUCCESS: Request is in correct status for upload")

    # 3. Validate file type
    file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    logger.info(f"[UPLOAD] Step 3: Validating file type: {file_ext}...")
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        logger.warning(f"[UPLOAD] FAILED: File type {file_ext} not allowed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_file_type",
                "message": f"File type {file_ext} not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}"
            }
        )
    logger.info(f"[UPLOAD] SUCCESS: File type {file_ext} is valid")

    # 4. Read and validate file size
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    logger.info(f"[UPLOAD] Step 4: Validating file size: {file_size_mb:.2f}MB...")

    if file_size_mb > settings.MAX_FILE_SIZE_MB:
        logger.warning(f"[UPLOAD] FAILED: File size {file_size_mb:.2f}MB exceeds limit")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "file_too_large",
                "message": f"File size {file_size_mb:.2f}MB exceeds limit of {settings.MAX_FILE_SIZE_MB}MB"
            }
        )
    logger.info(f"[UPLOAD] SUCCESS: File size {file_size_mb:.2f}MB is within limit")

    # 5. Save file to storage
    document_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"
    storage_dir = f"{settings.STORAGE_PATH}/uploads/{request_id}"
    os.makedirs(storage_dir, exist_ok=True)

    file_path = f"{storage_dir}/{document_id}{file_ext}"
    logger.info(f"[UPLOAD] Step 5: Saving file to {file_path}...")
    with open(file_path, "wb") as f:
        f.write(content)
    logger.info(f"[UPLOAD] SUCCESS: File saved as {document_id}")

    # 6. Update request
    logger.info(f"[UPLOAD] Step 6: Updating request status to VALIDATED...")
    request.document_storage_path = file_path
    request.status = RequestStatus.VALIDATED
    request.validated_at = datetime.utcnow()

    # 7. Create audit log
    logger.info(f"[UPLOAD] Step 7: Creating audit log entry...")
    audit = AuditLog.create(
        request_id=request_id,
        event_type=EventType.STATE_CHANGE,
        actor_type=ActorType.HUMAN,
        actor_id="staff_user",
        previous_state=RequestStatus.INTAKE_RECEIVED.value,
        new_state=RequestStatus.VALIDATED.value,
        action_details={
            "action": "upload_document",
            "document_id": document_id,
            "file_name": file.filename,
            "file_size_mb": round(file_size_mb, 2),
        },
    )
    db.add(audit)

    await db.commit()

    # 8. Queue for processing - dispatch Celery task
    logger.info(f"[UPLOAD] Step 8: Dispatching Celery task for AI processing...")
    request.status = RequestStatus.QUEUED

    # Import and dispatch Celery task
    from app.workers.tasks import process_document
    task = process_document.delay(request_id)
    logger.info(f"[UPLOAD] Celery task dispatched: {task.id}")

    audit2 = AuditLog.create(
        request_id=request_id,
        event_type=EventType.SYSTEM_EVENT,
        actor_type=ActorType.SYSTEM,
        actor_id="intake_service",
        previous_state=RequestStatus.VALIDATED.value,
        new_state=RequestStatus.QUEUED.value,
        action_details={"action": "queue_for_processing", "celery_task_id": task.id},
    )
    db.add(audit2)

    await db.commit()
    logger.info(f"[UPLOAD] SUCCESS: Document uploaded and request {request_id} queued for AI processing")

    return UploadResponse(
        request_id=request_id,
        status=RequestStatus.QUEUED,
        document_id=document_id,
        message="Document uploaded. Processing will begin shortly."
    )


@router.get(
    "",
    response_model=PaginatedRequests,
)
async def list_requests(
    customer_id: Optional[str] = Query(None),
    change_type: Optional[ChangeType] = Query(None),
    status_filter: Optional[RequestStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List requests with optional filters.

    **Filters:**
    - customer_id: Filter by customer
    - change_type: Filter by change type
    - status: Filter by status

    **Pagination:**
    - page: Page number (default: 1)
    - limit: Items per page (default: 20, max: 100)
    """
    # Build query
    query = select(PendingRequest)

    if customer_id:
        query = query.where(PendingRequest.customer_id == customer_id)
    if change_type:
        query = query.where(PendingRequest.change_type == change_type)
    if status_filter:
        query = query.where(PendingRequest.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.execute(count_query)
    total = total.scalar()

    # Apply pagination
    query = query.order_by(PendingRequest.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    requests = result.scalars().all()

    # Convert to response
    items = []
    for req in requests:
        items.append(RequestSummary(
            request_id=req.request_id,
            customer_id=req.customer_id,
            change_type=req.change_type,
            document_type=req.document_type,
            status=req.status,
            risk_tier=req.risk_tier,
            ai_recommendation=req.ai_recommendation,
            overall_confidence=float(req.overall_confidence) if req.overall_confidence else None,
            flags=req.flags or [],
            created_at=req.created_at,
        ))

    return PaginatedRequests(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit
    )


@router.get(
    "/{request_id}",
    response_model=RequestDetail,
    responses={
        404: {"model": ErrorResponse, "description": "Request not found"},
    }
)
async def get_request(
    request_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get full details of a request.

    Returns all information including:
    - Request details
    - Extracted values
    - Confidence scores
    - Forgery detection results
    - AI recommendation and summary
    - Current status and timestamps
    """
    request = await db.execute(
        select(PendingRequest).where(PendingRequest.request_id == request_id)
    )
    request = request.scalar_one_or_none()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "request_not_found", "message": f"Request {request_id} not found"}
        )

    # Build confidence breakdown
    confidence = None
    if request.overall_confidence:
        confidence = ConfidenceBreakdown(
            old_name_match=float(request.old_name_match_score) if request.old_name_match_score else None,
            new_name_match=float(request.new_name_match_score) if request.new_name_match_score else None,
            ocr_confidence=float(request.ocr_confidence) if request.ocr_confidence else None,
            extraction_confidence=float(request.extraction_confidence) if request.extraction_confidence else None,
            doc_authenticity=float(request.doc_authenticity_score) if request.doc_authenticity_score else None,
            overall=float(request.overall_confidence) if request.overall_confidence else None,
        )

    # Build forgery details
    forgery = None
    if request.forgery_result:
        details = request.forgery_details or {}
        forgery = ForgeryDetail(
            score=float(request.forgery_score) if request.forgery_score else 0,
            result=request.forgery_result,
            metadata_score=details.get("metadata"),
            ela_score=details.get("ela"),
            font_score=details.get("font"),
            ml_score=details.get("ml"),
        )

    # Build extraction details
    extraction_details = []
    if request.extraction_metadata:
        for field_name, field_data in request.extraction_metadata.items():
            if isinstance(field_data, dict):
                extraction_details.append(ExtractionDetail(
                    field_name=field_name,
                    value=field_data.get("value", ""),
                    confidence=field_data.get("confidence", 0),
                    source_snippet=field_data.get("source_snippet"),
                ))

    # Calculate time in current status
    time_in_status = None
    if request.created_at:
        delta = datetime.utcnow() - request.created_at
        time_in_status = int(delta.total_seconds() / 60)

    return RequestDetail(
        request_id=request.request_id,
        idempotency_key=request.idempotency_key,
        customer_id=request.customer_id,
        change_type=request.change_type,
        document_type=request.document_type,
        requested_old_value=request.requested_old_value,
        requested_new_value=request.requested_new_value,
        extracted_old_value=request.extracted_old_value,
        extracted_new_value=request.extracted_new_value,
        extraction_details=extraction_details,
        confidence=confidence,
        forgery=forgery,
        risk_tier=request.risk_tier,
        flags=request.flags or [],
        ai_recommendation=request.ai_recommendation,
        ai_summary=request.ai_summary,
        document_storage_path=request.document_storage_path,
        filenet_staging_id=request.filenet_staging_id,
        filenet_permanent_id=request.filenet_permanent_id,
        status=request.status,
        assigned_checker=request.assigned_checker,
        checker_decision=request.checker_decision,
        checker_decision_reason=request.checker_decision_reason,
        created_at=request.created_at,
        validated_at=request.validated_at,
        processing_started_at=request.processing_started_at,
        processing_completed_at=request.processing_completed_at,
        staged_at=request.staged_at,
        claimed_at=request.claimed_at,
        decided_at=request.decided_at,
        completed_at=request.completed_at,
        is_locked=request.is_locked,
        can_be_claimed=request.can_be_claimed,
        time_in_current_status_minutes=time_in_status,
    )


@router.delete(
    "/{request_id}",
    response_model=dict,
    responses={
        404: {"model": ErrorResponse, "description": "Request not found"},
    }
)
async def delete_request(
    request_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a request.

    This is primarily for development/testing purposes.
    In production, requests should typically be archived rather than deleted.
    """
    logger.info(f"[DELETE] Attempting to delete request: {request_id}")

    # Find the request
    request = await db.execute(
        select(PendingRequest).where(PendingRequest.request_id == request_id)
    )
    request = request.scalar_one_or_none()

    if not request:
        logger.warning(f"[DELETE] FAILED: Request {request_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "request_not_found", "message": f"Request {request_id} not found"}
        )

    # Delete associated audit logs first
    from sqlalchemy import delete as sql_delete
    await db.execute(
        sql_delete(AuditLog).where(AuditLog.request_id == request_id)
    )

    # Delete the request
    await db.delete(request)
    await db.commit()

    logger.info(f"[DELETE] SUCCESS: Request {request_id} deleted")

    return {
        "message": f"Request {request_id} deleted successfully",
        "request_id": request_id
    }
