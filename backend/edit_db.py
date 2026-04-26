"""
Database Edit Utility

Quick script to edit database records for testing.
Run with: python edit_db.py
"""

import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models import Request, RequestStatus


async def list_requests():
    """List all requests with key info."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Request).order_by(Request.created_at.desc()).limit(20)
        )
        requests = result.scalars().all()

        print("\n" + "="*80)
        print("REQUESTS")
        print("="*80)
        for req in requests:
            print(f"{req.request_id} | {req.status.value:30} | {req.customer_id} | {req.requested_old_value} → {req.requested_new_value}")
        print("="*80 + "\n")


async def reset_request_to_pending(request_id: str):
    """Reset a request back to AI_VERIFIED_PENDING_HUMAN for re-testing."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Request).where(Request.request_id == request_id)
        )
        request = result.scalar_one_or_none()

        if not request:
            print(f"Request {request_id} not found!")
            return

        old_status = request.status.value
        request.status = RequestStatus.AI_VERIFIED_PENDING_HUMAN
        request.assigned_checker = None
        request.checker_lock_until = None
        request.checker_decision = None
        request.checker_decision_reason = None
        request.decided_at = None
        request.completed_at = None

        await session.commit()
        print(f"✓ Reset {request_id}: {old_status} → AI_VERIFIED_PENDING_HUMAN")


async def reset_all_to_pending():
    """Reset ALL completed/rejected requests back to pending for re-testing."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Request).where(
                Request.status.in_([
                    RequestStatus.APPROVED,
                    RequestStatus.REJECTED,
                    RequestStatus.COMPLETED,
                    RequestStatus.IN_REVIEW
                ])
            )
        )
        requests = result.scalars().all()

        count = 0
        for req in requests:
            if req.document_storage_path:  # Only reset requests that have documents
                req.status = RequestStatus.AI_VERIFIED_PENDING_HUMAN
                req.assigned_checker = None
                req.checker_lock_until = None
                req.checker_decision = None
                req.checker_decision_reason = None
                req.decided_at = None
                req.completed_at = None
                count += 1

        await session.commit()
        print(f"✓ Reset {count} requests to AI_VERIFIED_PENDING_HUMAN")


async def delete_request(request_id: str):
    """Delete a request completely."""
    async with AsyncSessionLocal() as session:
        from app.models import AuditLog

        # Delete audit logs first
        from sqlalchemy import delete as sql_delete
        await session.execute(
            sql_delete(AuditLog).where(AuditLog.request_id == request_id)
        )

        # Delete request
        result = await session.execute(
            select(Request).where(Request.request_id == request_id)
        )
        request = result.scalar_one_or_none()

        if request:
            await session.delete(request)
            await session.commit()
            print(f"✓ Deleted {request_id}")
        else:
            print(f"Request {request_id} not found!")


async def update_request_field(request_id: str, field: str, value):
    """Update a specific field on a request."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Request).where(Request.request_id == request_id)
        )
        request = result.scalar_one_or_none()

        if not request:
            print(f"Request {request_id} not found!")
            return

        if hasattr(request, field):
            old_value = getattr(request, field)
            setattr(request, field, value)
            await session.commit()
            print(f"✓ Updated {request_id}.{field}: {old_value} → {value}")
        else:
            print(f"Field '{field}' not found on Request model!")


async def main():
    """Interactive menu."""
    while True:
        print("\n" + "="*50)
        print("DATABASE EDIT UTILITY")
        print("="*50)
        print("1. List all requests")
        print("2. Reset specific request to PENDING_HUMAN")
        print("3. Reset ALL completed requests to PENDING_HUMAN")
        print("4. Delete a request")
        print("5. Update a field on a request")
        print("6. Exit")
        print("="*50)

        choice = input("Choice: ").strip()

        if choice == "1":
            await list_requests()

        elif choice == "2":
            request_id = input("Request ID (e.g., REQ-BBABA05D): ").strip()
            await reset_request_to_pending(request_id)

        elif choice == "3":
            confirm = input("Reset ALL completed requests? (yes/no): ").strip()
            if confirm.lower() == "yes":
                await reset_all_to_pending()

        elif choice == "4":
            request_id = input("Request ID to delete: ").strip()
            confirm = input(f"Really delete {request_id}? (yes/no): ").strip()
            if confirm.lower() == "yes":
                await delete_request(request_id)

        elif choice == "5":
            request_id = input("Request ID: ").strip()
            field = input("Field name (e.g., status, risk_tier, ai_recommendation): ").strip()
            value = input("New value: ").strip()

            # Handle enum conversions
            if field == "status":
                value = RequestStatus(value)

            await update_request_field(request_id, field, value)

        elif choice == "6":
            print("Bye!")
            break

        else:
            print("Invalid choice!")


if __name__ == "__main__":
    asyncio.run(main())
