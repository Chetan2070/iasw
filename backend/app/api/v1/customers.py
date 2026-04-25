"""
Customer Management API

Endpoints for managing customer records (Mock RPS).
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.customer import Customer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers", tags=["customers"])


# ===================
# Schemas
# ===================

class CustomerCreate(BaseModel):
    """Schema for creating a new customer."""
    customer_id: str
    full_name: str
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    account_number: str
    account_type: Optional[str] = "SAVINGS"
    branch_code: Optional[str] = None


class CustomerUpdate(BaseModel):
    """Schema for updating a customer."""
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    account_type: Optional[str] = None
    branch_code: Optional[str] = None


class CustomerResponse(BaseModel):
    """Schema for customer response."""
    customer_id: str
    full_name: str
    date_of_birth: Optional[str]
    address: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    account_number: Optional[str]
    account_type: Optional[str]
    branch_code: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class CustomerListResponse(BaseModel):
    """Schema for customer list response."""
    items: list[CustomerResponse]
    total: int
    page: int
    limit: int


# ===================
# Endpoints
# ===================

@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    data: CustomerCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new customer record.

    This simulates adding a customer to the core banking system (RPS).
    """
    # Check if customer_id already exists
    existing = await db.execute(
        select(Customer).where(Customer.customer_id == data.customer_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Customer with ID {data.customer_id} already exists"
        )

    # Check if account_number already exists
    existing_account = await db.execute(
        select(Customer).where(Customer.account_number == data.account_number)
    )
    if existing_account.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Account number {data.account_number} already exists"
        )

    customer = Customer(
        customer_id=data.customer_id,
        full_name=data.full_name,
        date_of_birth=data.date_of_birth,
        address=data.address,
        email=data.email,
        phone=data.phone,
        account_number=data.account_number,
        account_type=data.account_type,
        branch_code=data.branch_code,
    )

    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    logger.info(f"Created customer: {customer.customer_id} - {customer.full_name}")

    return customer


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all customers with pagination.

    Optionally search by name or account number.
    """
    query = select(Customer)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Customer.full_name.ilike(search_pattern)) |
            (Customer.account_number.ilike(search_pattern)) |
            (Customer.customer_id.ilike(search_pattern))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Apply pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit).order_by(Customer.created_at.desc())

    result = await db.execute(query)
    customers = result.scalars().all()

    return CustomerListResponse(
        items=customers,
        total=total,
        page=page,
        limit=limit
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific customer by ID."""
    result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found"
        )

    return customer


@router.get("/account/{account_number}", response_model=CustomerResponse)
async def get_customer_by_account(
    account_number: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a customer by account number."""
    result = await db.execute(
        select(Customer).where(Customer.account_number == account_number)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No customer found with account number {account_number}"
        )

    return customer


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    data: CustomerUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a customer's details."""
    result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found"
        )

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)

    customer.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(customer)

    logger.info(f"Updated customer: {customer.customer_id}")

    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a customer record."""
    result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found"
        )

    await db.delete(customer)
    await db.commit()

    logger.info(f"Deleted customer: {customer_id}")
