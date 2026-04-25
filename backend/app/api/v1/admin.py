"""
Admin API endpoints for database inspection and management.

WARNING: This is for development/debugging only.
Do NOT expose in production without proper authentication.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func, desc

from app.db import get_db
from app.models.user import User
from app.models.audit import AuditLog
from app.models.enums import ActorType

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/tables")
async def get_all_tables(db: AsyncSession = Depends(get_db)):
    """
    Get data from all main tables for debugging.

    Returns a dict with table names as keys and {columns, rows} as values.
    """
    tables_data = {}

    # Define tables to fetch with their key columns first
    tables_config = [
        ("customers", ["customer_id", "full_name", "email", "updated_by", "updated_at"]),
        ("requests", [
            "request_id", "customer_id", "status", "change_type", "document_type",
            "requested_old_value", "requested_new_value", "extracted_old_value", "extracted_new_value",
            "overall_confidence", "risk_tier", "ai_recommendation", "checker_decision",
            "assigned_checker", "decided_at", "created_at"
        ]),
        ("audit_logs", [
            "audit_id", "request_id", "event_type", "actor_type", "actor_id",
            "previous_state", "new_state", "timestamp"
        ]),
        ("users", [
            "id", "username", "email", "role", "is_active", "created_at", "last_login"
        ]),
    ]

    for table_name, columns in tables_config:
        try:
            # Build column list for SELECT
            col_list = ", ".join(columns)
            query = text(f"SELECT {col_list} FROM {table_name} ORDER BY 1 DESC LIMIT 50")
            result = await db.execute(query)
            rows = result.fetchall()

            tables_data[table_name] = {
                "columns": columns,
                "rows": [dict(zip(columns, row)) for row in rows]
            }
        except Exception as e:
            tables_data[table_name] = {
                "columns": ["error"],
                "rows": [{"error": str(e)}]
            }

    return tables_data


@router.get("/users")
async def get_users(
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None, description="Search by username or email"),
    role: Optional[str] = Query(None, description="Filter by role"),
    status: Optional[str] = Query(None, description="Filter by status (active/inactive)"),
):
    """
    Get all users with optional filtering.

    Returns list of users with stats.
    """
    query = select(User).order_by(desc(User.created_at))

    # Apply filters
    if search:
        query = query.where(
            (User.username.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
        )
    if role:
        query = query.where(User.role == role)
    if status:
        is_active = status.lower() == "active"
        query = query.where(User.is_active == is_active)

    result = await db.execute(query)
    users = result.scalars().all()

    # Get stats
    total_result = await db.execute(select(func.count(User.id)))
    total = total_result.scalar()

    admin_result = await db.execute(select(func.count(User.id)).where(User.role == "admin"))
    admin_count = admin_result.scalar()

    staff_result = await db.execute(select(func.count(User.id)).where(User.role == "staff"))
    staff_count = staff_result.scalar()

    checker_result = await db.execute(select(func.count(User.id)).where(User.role == "checker"))
    checker_count = checker_result.scalar()

    active_result = await db.execute(select(func.count(User.id)).where(User.is_active == True))
    active_count = active_result.scalar()

    return {
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role.value if u.role else None,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login": u.last_login.isoformat() if u.last_login else None,
            }
            for u in users
        ],
        "stats": {
            "total": total,
            "admin": admin_count,
            "staff": staff_count,
            "checker": checker_count,
            "active": active_count,
            "inactive": total - active_count,
        }
    }


@router.get("/audit-logs")
async def get_audit_logs(
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None, description="Search in actor_id or request_id"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    actor_type: Optional[str] = Query(None, description="Filter by actor type (human/ai/system)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Get audit logs with pagination and filtering.

    Returns paginated list of audit logs with stats.
    """
    # Base query
    query = select(AuditLog).order_by(desc(AuditLog.timestamp))

    # Map frontend actor_type values to database enum values
    actor_type_map = {
        "human": ActorType.HUMAN,
        "ai": ActorType.AI_AGENT,
        "system": ActorType.SYSTEM,
    }
    mapped_actor_type = actor_type_map.get(actor_type.lower()) if actor_type else None

    # Apply filters
    if search:
        query = query.where(
            (AuditLog.actor_id.ilike(f"%{search}%")) |
            (AuditLog.request_id.ilike(f"%{search}%"))
        )
    if event_type:
        query = query.where(AuditLog.event_type == event_type)
    if mapped_actor_type:
        query = query.where(AuditLog.actor_type == mapped_actor_type)

    # Get total count
    count_query = select(func.count(AuditLog.audit_id))
    if search:
        count_query = count_query.where(
            (AuditLog.actor_id.ilike(f"%{search}%")) |
            (AuditLog.request_id.ilike(f"%{search}%"))
        )
    if event_type:
        count_query = count_query.where(AuditLog.event_type == event_type)
    if mapped_actor_type:
        count_query = count_query.where(AuditLog.actor_type == mapped_actor_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    # Get stats
    total_all = await db.execute(select(func.count(AuditLog.audit_id)))
    total_all_count = total_all.scalar()

    human_count_result = await db.execute(
        select(func.count(AuditLog.audit_id)).where(AuditLog.actor_type == ActorType.HUMAN)
    )
    human_count = human_count_result.scalar() or 0

    ai_count_result = await db.execute(
        select(func.count(AuditLog.audit_id)).where(AuditLog.actor_type == ActorType.AI_AGENT)
    )
    ai_count = ai_count_result.scalar() or 0

    system_count_result = await db.execute(
        select(func.count(AuditLog.audit_id)).where(AuditLog.actor_type == ActorType.SYSTEM)
    )
    system_count = system_count_result.scalar() or 0

    unique_users_result = await db.execute(
        select(func.count(func.distinct(AuditLog.actor_id)))
    )
    unique_users = unique_users_result.scalar()

    # Helper to convert actor_type enum to frontend format
    def actor_type_to_frontend(actor_type_enum):
        if not actor_type_enum:
            return None
        mapping = {
            ActorType.HUMAN: "human",
            ActorType.AI_AGENT: "ai",
            ActorType.SYSTEM: "system",
        }
        return mapping.get(actor_type_enum, actor_type_enum.value.lower())

    return {
        "logs": [
            {
                "id": str(log.audit_id),
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "request_id": log.request_id,
                "event_type": log.event_type.value if log.event_type else None,
                "actor_type": actor_type_to_frontend(log.actor_type),
                "actor_id": log.actor_id,
                "previous_state": log.previous_state,
                "new_state": log.new_state,
                "agent_name": log.agent_name,
                "action_details": log.action_details,
            }
            for log in logs
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
        "stats": {
            "total": total_all_count,
            "human": human_count,
            "ai": ai_count,
            "system": system_count,
            "unique_users": unique_users,
        }
    }
