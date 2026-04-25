"""
Database Seed Script

Seeds the database with initial mock data for testing.
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, init_db
from app.models import Customer, Checker


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
            email="Sumeet.kumar@email.com",
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


async def main():
    """Run database seeding."""
    print("Initializing database...")
    await init_db()

    print("\nSeeding database...")
    async with AsyncSessionLocal() as session:
        await seed_customers(session)
        await seed_checkers(session)

    print("\nDatabase seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())
