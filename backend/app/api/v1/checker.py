"""
Checker Endpoints

API endpoints for checker workbench operations.
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.db.session import get_db
from app.config import settings
from app.models import (
    Request, Customer, AuditLog,
    RequestStatus, RiskTier, Recommendation, Decision,
    ActorType, EventType
)
from app.schemas import (
    QueueItem, QueueResponse, QueueFilters,
    ClaimResponse, DecisionRequest, DecisionResponse, ReleaseResponse,
    ReviewData, FieldScore, ErrorResponse
)

router = APIRouter()

# Lock duration in minutes
LOCK_DURATION_MINUTES = 15


@router.get(
    "/queue",
    response_model=QueueResponse,
)
async def get_queue(
    risk_tier: Optional[RiskTier] = Query(None),
    ai_recommendation: Optional[Recommendation] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the queue of requests pending human review.

    **Filters:**
    - risk_tier: Filter by risk level (LOW, MEDIUM, HIGH)
    - ai_recommendation: Filter by AI recommendation

    **Note:** Only returns requests with status AI_VERIFIED_PENDING_HUMAN
    that are not currently locked by another checker.
    """
    # Build query - only show requests ready for review and not locked
    now = datetime.utcnow()
    query = select(Request).where(
        and_(
            Request.status == RequestStatus.AI_VERIFIED_PENDING_HUMAN,
            # Not locked OR lock has expired
            (Request.checker_lock_until == None) | (Request.checker_lock_until < now)
        )
    )

    if risk_tier:
        query = query.where(Request.risk_tier == risk_tier)
    if ai_recommendation:
        query = query.where(Request.ai_recommendation == ai_recommendation)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.execute(count_query)
    total = total.scalar()

    # Order by risk tier (HIGH first) then by staged_at
    query = query.order_by(
        # HIGH = 0, MEDIUM = 1, LOW = 2 for sorting
        Request.risk_tier.desc(),
        Request.staged_at.asc()
    )
    query = query.offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    requests = result.scalars().all()

    # Convert to response
    items = []
    for req in requests:
        time_in_queue = 0
        if req.staged_at:
            delta = now - req.staged_at
            time_in_queue = int(delta.total_seconds() / 60)

        items.append(QueueItem(
            request_id=req.request_id,
            customer_id=req.customer_id,
            change_type=req.change_type,
            document_type=req.document_type,
            risk_tier=req.risk_tier or RiskTier.MEDIUM,
            ai_recommendation=req.ai_recommendation or Recommendation.MANUAL_REVIEW,
            overall_score=float(req.overall_confidence) if req.overall_confidence else 0.0,
            flags=req.flags or [],
            queued_at=req.staged_at or req.created_at,
            time_in_queue_minutes=time_in_queue,
        ))

    return QueueResponse(
        items=items,
        total=total,
        page=page,
        limit=limit
    )


@router.post(
    "/claim/{request_id}",
    response_model=ClaimResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Request not found"},
        409: {"model": ErrorResponse, "description": "Request already claimed"},
    }
)
async def claim_request(
    request_id: str,
    checker_id: str = Query(..., description="Checker's ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Claim a request for review.

    The checker has 15 minutes to complete their review.
    If the lock expires, the request is automatically released.

    **HITL Enforcement:** This action is only available to human checkers.
    """
    # 1. Check request exists
    request = await db.execute(
        select(Request).where(Request.request_id == request_id)
    )
    request = request.scalar_one_or_none()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "request_not_found", "message": f"Request {request_id} not found"}
        )

    # 2. Check request is in correct status
    if request.status != RequestStatus.AI_VERIFIED_PENDING_HUMAN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_status",
                "message": f"Request is in status {request.status.value}, cannot be claimed"
            }
        )

    # 3. Check if already locked by another checker
    now = datetime.utcnow()
    if request.is_locked and request.assigned_checker != checker_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "already_claimed",
                "message": f"Request is already claimed by {request.assigned_checker}"
            }
        )

    # 4. Claim the request
    lock_expires = now + timedelta(minutes=LOCK_DURATION_MINUTES)
    previous_state = request.status.value

    request.status = RequestStatus.IN_REVIEW
    request.assigned_checker = checker_id
    request.checker_lock_until = lock_expires
    request.claimed_at = now

    # 5. Create audit log
    audit = AuditLog.create(
        request_id=request_id,
        event_type=EventType.HUMAN_ACTION,
        actor_type=ActorType.HUMAN,
        actor_id=checker_id,
        previous_state=previous_state,
        new_state=RequestStatus.IN_REVIEW.value,
        action_details={
            "action": "claim_request",
            "lock_expires_at": lock_expires.isoformat(),
        },
    )
    db.add(audit)

    await db.commit()

    return ClaimResponse(
        request_id=request_id,
        status=RequestStatus.IN_REVIEW.value,
        assigned_to=checker_id,
        lock_expires_at=lock_expires,
        message=f"Request claimed successfully. You have {LOCK_DURATION_MINUTES} minutes to review."
    )


@router.post(
    "/decide/{request_id}",
    response_model=DecisionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid decision"},
        403: {"model": ErrorResponse, "description": "Not authorized"},
        404: {"model": ErrorResponse, "description": "Request not found"},
    }
)
async def submit_decision(
    request_id: str,
    decision_data: DecisionRequest,
    checker_id: str = Query(..., description="Checker's ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a decision for a claimed request.

    **Decisions:**
    - APPROVE: Triggers RPS update (core banking)
    - REJECT: Requires reason, notifies branch
    - MORE_INFO: Requires reason, allows customer resubmit
    - ESCALATE: Requires reason, routes to senior checker

    **HITL Enforcement:**
    This is the critical HITL boundary. Only human checkers can approve
    or reject requests. The RPS update is ONLY triggered by human approval.
    """
    # 1. Check request exists
    request = await db.execute(
        select(Request).where(Request.request_id == request_id)
    )
    request = request.scalar_one_or_none()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "request_not_found", "message": f"Request {request_id} not found"}
        )

    # 2. Verify checker owns the lock
    if request.assigned_checker != checker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "not_authorized",
                "message": f"Request is assigned to {request.assigned_checker}, not {checker_id}"
            }
        )

    # 3. Check lock hasn't expired
    if not request.is_locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "lock_expired",
                "message": "Your lock has expired. Please reclaim the request."
            }
        )

    # 4. Validate reason is provided for certain decisions
    if decision_data.decision in [Decision.REJECT, Decision.MORE_INFO, Decision.ESCALATE]:
        if not decision_data.reason or len(decision_data.reason.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "reason_required",
                    "message": f"Reason is required for {decision_data.decision.value} decision"
                }
            )

    # 5. Process the decision
    now = datetime.utcnow()
    previous_state = request.status.value
    rps_updated = False

    if decision_data.decision == Decision.APPROVE:
        # HITL BOUNDARY: Human approval triggers RPS update
        request.status = RequestStatus.APPROVED
        request.checker_decision = Decision.APPROVE
        request.decided_at = now

        # Simulate RPS update (in production, this would call actual RPS service)
        # The RPS service would verify actor_type == HUMAN before processing
        rps_updated = True
        request.status = RequestStatus.COMPLETED
        request.completed_at = now

        # Update customer record (mock RPS)
        customer = await db.execute(
            select(Customer).where(Customer.customer_id == request.customer_id)
        )
        customer = customer.scalar_one_or_none()
        if customer:
            # Update the appropriate field based on change type
            if request.change_type.value == "LEGAL_NAME":
                customer.full_name = request.requested_new_value
                customer.updated_by = checker_id
            # Add other change types as needed

        new_state = RequestStatus.COMPLETED.value

    elif decision_data.decision == Decision.REJECT:
        request.status = RequestStatus.REJECTED
        request.checker_decision = Decision.REJECT
        request.checker_decision_reason = decision_data.reason
        request.decided_at = now
        new_state = RequestStatus.REJECTED.value

    elif decision_data.decision == Decision.MORE_INFO:
        request.status = RequestStatus.PENDING_INFO
        request.checker_decision = Decision.MORE_INFO
        request.checker_decision_reason = decision_data.reason
        request.decided_at = now
        # Check resubmit limit
        if request.resubmit_count >= request.max_resubmits:
            request.status = RequestStatus.ESCALATED
            new_state = RequestStatus.ESCALATED.value
        else:
            new_state = RequestStatus.PENDING_INFO.value

    elif decision_data.decision == Decision.ESCALATE:
        request.status = RequestStatus.ESCALATED
        request.checker_decision = Decision.ESCALATE
        request.checker_decision_reason = decision_data.reason
        request.decided_at = now
        new_state = RequestStatus.ESCALATED.value

    # Clear lock
    request.checker_lock_until = None

    # 6. Create audit log
    audit = AuditLog.create(
        request_id=request_id,
        event_type=EventType.HUMAN_ACTION,
        actor_type=ActorType.HUMAN,  # CRITICAL: This MUST be HUMAN
        actor_id=checker_id,
        previous_state=previous_state,
        new_state=new_state,
        action_details={
            "action": "submit_decision",
            "decision": decision_data.decision.value,
            "reason": decision_data.reason,
            "rps_updated": rps_updated,
            "ai_recommendation": request.ai_recommendation.value if request.ai_recommendation else None,
            "override": request.ai_recommendation and request.ai_recommendation.value != decision_data.decision.value,
        },
        record_snapshot=request.to_dict(),
    )
    db.add(audit)

    await db.commit()

    # Determine message
    if decision_data.decision == Decision.APPROVE:
        message = "Decision recorded. Core banking updated successfully."
    elif decision_data.decision == Decision.REJECT:
        message = "Request rejected. Branch has been notified."
    elif decision_data.decision == Decision.MORE_INFO:
        message = "Request pending additional information. Customer will be notified."
    else:
        message = "Request escalated to senior reviewer."

    return DecisionResponse(
        request_id=request_id,
        decision=decision_data.decision,
        new_status=request.status,
        rps_updated=rps_updated,
        message=message
    )


@router.post(
    "/release/{request_id}",
    response_model=ReleaseResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Request not found"},
    }
)
async def release_request(
    request_id: str,
    checker_id: str = Query(..., description="Checker's ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Release a claimed request back to the queue.

    Use this if you cannot complete the review within the time limit
    or need to reassign the request.
    """
    # 1. Check request exists
    request = await db.execute(
        select(Request).where(Request.request_id == request_id)
    )
    request = request.scalar_one_or_none()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "request_not_found", "message": f"Request {request_id} not found"}
        )

    # 2. Verify checker owns the lock (allow if no checker assigned - already released)
    if request.assigned_checker and request.assigned_checker != checker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "not_authorized",
                "message": f"Request is assigned to {request.assigned_checker}, not {checker_id}"
            }
        )

    # 3. Don't release if already decided/completed - just return success
    terminal_statuses = [
        RequestStatus.REJECTED,
        RequestStatus.COMPLETED,
        RequestStatus.APPROVED,
        RequestStatus.ESCALATED,
        RequestStatus.FAILED,
    ]
    if request.status in terminal_statuses or request.checker_decision is not None:
        return ReleaseResponse(
            request_id=request_id,
            status=request.status.value,
            message="Request already decided, no release needed."
        )

    # 4. Release the request
    previous_state = request.status.value
    request.status = RequestStatus.AI_VERIFIED_PENDING_HUMAN
    request.assigned_checker = None
    request.checker_lock_until = None

    # 5. Create audit log
    audit = AuditLog.create(
        request_id=request_id,
        event_type=EventType.HUMAN_ACTION,
        actor_type=ActorType.HUMAN,
        actor_id=checker_id,
        previous_state=previous_state,
        new_state=RequestStatus.AI_VERIFIED_PENDING_HUMAN.value,
        action_details={"action": "release_request"},
    )
    db.add(audit)

    await db.commit()

    return ReleaseResponse(
        request_id=request_id,
        status=RequestStatus.AI_VERIFIED_PENDING_HUMAN.value,
        message="Request released back to queue."
    )


@router.get(
    "/review/{request_id}",
    response_model=ReviewData,
    responses={
        404: {"model": ErrorResponse, "description": "Request not found"},
    }
)
async def get_review_data(
    request_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete review data for the checker UI.

    Returns all information needed for the checker to make a decision:
    - Request details
    - Extracted values with confidence scores
    - Forgery detection results
    - AI recommendation and summary
    - Document reference
    """
    request = await db.execute(
        select(Request).where(Request.request_id == request_id)
    )
    request = request.scalar_one_or_none()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "request_not_found", "message": f"Request {request_id} not found"}
        )

    # Build field scores
    field_scores = []
    if request.old_name_match_score is not None:
        field_scores.append(FieldScore(
            field_name="old_name",
            extracted_value=request.extracted_old_value or "",
            expected_value=request.requested_old_value,
            match_score=float(request.old_name_match_score),
        ))
    if request.new_name_match_score is not None:
        field_scores.append(FieldScore(
            field_name="new_name",
            extracted_value=request.extracted_new_value or "",
            expected_value=request.requested_new_value,
            match_score=float(request.new_name_match_score),
        ))

    return ReviewData(
        request_id=request.request_id,
        customer_id=request.customer_id,
        change_type=request.change_type,
        document_type=request.document_type,
        requested_old_value=request.requested_old_value,
        requested_new_value=request.requested_new_value,
        extracted_old_value=request.extracted_old_value,
        extracted_new_value=request.extracted_new_value,
        field_scores=field_scores,
        ocr_confidence=float(request.ocr_confidence) if request.ocr_confidence else None,
        extraction_confidence=float(request.extraction_confidence) if request.extraction_confidence else None,
        doc_authenticity_score=float(request.doc_authenticity_score) if request.doc_authenticity_score else None,
        overall_score=float(request.overall_confidence) if request.overall_confidence else None,
        forgery_score=float(request.forgery_score) if request.forgery_score else None,
        forgery_result=request.forgery_result.value if request.forgery_result else None,
        forgery_details=request.forgery_details,
        risk_tier=request.risk_tier,
        flags=request.flags or [],
        ai_recommendation=request.ai_recommendation,
        ai_summary=request.ai_summary,
        document_url=f"/api/v1/documents/{request.request_id}" if request.document_storage_path else None,
        filenet_reference=request.filenet_staging_id,
        created_at=request.created_at,
        staged_at=request.staged_at,
        claimed_at=request.claimed_at,
        assigned_checker=request.assigned_checker,
    )


# Response model for review history
from pydantic import BaseModel
from typing import List


class ReviewHistoryItem(BaseModel):
    request_id: str
    customer_id: str
    change_type: str
    document_type: str
    decision: str
    decision_reason: Optional[str]
    decided_at: datetime
    reviewed_by: str
    ai_recommendation: Optional[str]
    risk_tier: Optional[str]
    overall_score: Optional[float]


class ReviewHistoryResponse(BaseModel):
    items: List[ReviewHistoryItem]
    total: int
    page: int
    limit: int


@router.get(
    "/reviews",
    response_model=ReviewHistoryResponse,
)
async def get_review_history(
    checker_id: str = Query(..., description="Checker's ID to filter reviews"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get completed reviews for a specific checker.

    Returns all requests that have been decided by the specified checker,
    ordered by decision date (most recent first).
    """
    # Build query - get requests where this checker made a decision
    query = select(Request).where(
        and_(
            Request.assigned_checker == checker_id,
            Request.checker_decision.isnot(None)
        )
    ).order_by(Request.decided_at.desc())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    requests = result.scalars().all()

    # Convert to response
    items = []
    for req in requests:
        items.append(ReviewHistoryItem(
            request_id=req.request_id,
            customer_id=req.customer_id,
            change_type=req.change_type.value,
            document_type=req.document_type.value,
            decision=req.checker_decision.value if req.checker_decision else "UNKNOWN",
            decision_reason=req.checker_decision_reason,
            decided_at=req.decided_at,
            reviewed_by=req.assigned_checker,
            ai_recommendation=req.ai_recommendation.value if req.ai_recommendation else None,
            risk_tier=req.risk_tier.value if req.risk_tier else None,
            overall_score=float(req.overall_confidence) if req.overall_confidence else None,
        ))

    return ReviewHistoryResponse(
        items=items,
        total=total,
        page=page,
        limit=limit
    )
