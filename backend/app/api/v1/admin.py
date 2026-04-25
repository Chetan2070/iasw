"""
Admin API endpoints for database inspection.

WARNING: This is for development/debugging only.
Do NOT expose in production without proper authentication.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import get_db

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
