"""
Database Seed Script

Seeds the database with initial mock data for testing.
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal, init_db
from app.models import Customer, Checker, User, UserRole
from app.utils.security import hash_password


async def seed_customers(session: AsyncSession):
    """Seed mock customer data."""
    customers = [
        Customer(
            customer_id="C001",
            full_name="Priya Sharma",
            date_of_birth="1990-05-15",
            address="123 MG Road, Mumbai, Maharashtra 400001",
            email="priya.sharma@email.com",
            phone="+91-9876543210",
            account_number="1234567890",
            account_type="SAVINGS",
            branch_code="MUM001",
        ),
        Customer(
            customer_id="C002",
            full_name="Rahul Mehta",
            date_of_birth="1988-08-22",
            address="456 Park Street, Kolkata, West Bengal 700016",
            email="rahul.mehta@email.com",
            phone="+91-9876543211",
            account_number="1234567891",
            account_type="CURRENT",
            branch_code="KOL001",
        ),
        Customer(
            customer_id="C003",
            full_name="Anita Singh",
            date_of_birth="1992-12-01",
            address="789 Brigade Road, Bangalore, Karnataka 560001",
            email="anita.singh@email.com",
            phone="+91-9876543212",
            account_number="1234567892",
            account_type="SAVINGS",
            branch_code="BLR001",
        ),
        Customer(
            customer_id="C004",
            full_name="Vikram Patel",
            date_of_birth="1985-03-10",
            address="321 Connaught Place, New Delhi 110001",
            email="vikram.patel@email.com",
            phone="+91-9876543213",
            account_number="1234567893",
            account_type="SAVINGS",
            branch_code="DEL001",
        ),
        Customer(
            customer_id="C005",
            full_name="Nivedita Mondal",
            date_of_birth="1995-07-28",
            address="654 Banjara Hills, Hyderabad, Telangana 500034",
            email="nivedita.mondal@email.com",
            phone="+91-9876543214",
            account_number="1234567894",
            account_type="SAVINGS",
            branch_code="HYD001",
        ),
        Customer(
            customer_id="C006",
            full_name="Sumeet Kumar",
            date_of_birth="1991-09-18",
            address="42 Sector 15, Gurgaon, Haryana 122001",
            email="sumeet.kumar@email.com",
            phone="+91-9876543215",
            account_number="1234567895",
            account_type="SAVINGS",
            branch_code="GUR001",
        ),
    ]

    for customer in customers:
        # Check if exists
        existing = await session.get(Customer, customer.customer_id)
        if not existing:
            session.add(customer)
            print(f"Added customer: {customer.customer_id} - {customer.full_name}")

    await session.commit()


async def seed_checkers(session: AsyncSession):
    """Seed mock checker data."""
    checkers = [
        Checker(
            checker_id="checker_jane",
            name="Jane Smith",
            email="jane.smith@bank.com",
            is_senior="false",
            is_active="true",
        ),
        Checker(
            checker_id="checker_john",
            name="John Doe",
            email="john.doe@bank.com",
            is_senior="false",
            is_active="true",
        ),
        Checker(
            checker_id="checker_senior",
            name="Sarah Johnson",
            email="sarah.johnson@bank.com",
            is_senior="true",
            is_active="true",
        ),
    ]

    for checker in checkers:
        existing = await session.get(Checker, checker.checker_id)
        if not existing:
            session.add(checker)
            print(f"Added checker: {checker.checker_id} - {checker.name}")

    await session.commit()


async def seed_users(session: AsyncSession):
    """Seed user accounts for authentication."""
    # Get existing checkers to create linked user accounts
    result = await session.execute(select(Checker))
    checkers = result.scalars().all()

    users = [
        # Admin user
        User(
            id="USR-ADMIN001",
            username="admin",
            email="admin@iasw.local",
            password_hash=hash_password("admin123"),
            role=UserRole.ADMIN,
            is_active=True,
        ),
        # Staff user
        User(
            id="USR-STAFF001",
            username="staff",
            email="staff@iasw.local",
            password_hash=hash_password("staff123"),
            role=UserRole.STAFF,
            is_active=True,
        ),
    ]

    # Create user accounts for each checker
    for checker in checkers:
        users.append(User(
            id=f"USR-{checker.checker_id.upper().replace('_', '')}",
            username=checker.checker_id,
            email=checker.email or f"{checker.checker_id}@iasw.local",
            password_hash=hash_password("checker123"),
            role=UserRole.CHECKER,
            checker_id=checker.checker_id,
            is_active=checker.is_active == "true",
        ))

    for user in users:
        existing = await session.get(User, user.id)
        if not existing:
            # Also check by username
            result = await session.execute(
                select(User).where(User.username == user.username)
            )
            if not result.scalar_one_or_none():
                session.add(user)
                print(f"Added user: {user.username} ({user.role.value})")

    await session.commit()


async def main():
    """Run database seeding."""
    print("Initializing database...")
    await init_db()

    print("\nSeeding database...")
    async with AsyncSessionLocal() as session:
        await seed_customers(session)
        await seed_checkers(session)
        await seed_users(session)

    print("\nDatabase seeding complete!")
    print("\nTest credentials:")
    print("  admin / admin123 (admin role)")
    print("  staff / staff123 (staff role)")
    print("  checker_jane / checker123 (checker role)")
    print("  checker_john / checker123 (checker role)")
    print("  checker_senior / checker123 (checker role)")


if __name__ == "__main__":
    asyncio.run(main())
