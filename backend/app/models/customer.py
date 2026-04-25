"""
Customer Model (Mock RPS)

Mock representation of core banking customer records.
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func

from app.db.session import Base


class Customer(Base):
    """
    Mock RPS customer record.

    In production, this would be replaced with actual RPS integration.
    """

    __tablename__ = "customers"

    # ===================
    # Identity
    # ===================
    customer_id = Column(String(20), primary_key=True, index=True)

    # ===================
    # Personal Details
    # ===================
    full_name = Column(String(255), nullable=False)
    date_of_birth = Column(String(10), nullable=True)  # YYYY-MM-DD
    address = Column(String(500), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)

    # ===================
    # Account Details
    # ===================
    account_number = Column(String(20), nullable=True, unique=True, index=True)
    account_type = Column(String(50), nullable=True)
    branch_code = Column(String(10), nullable=True)

    # ===================
    # Metadata
    # ===================
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    updated_by = Column(String(50), nullable=True)

    def __repr__(self):
        return f"<Customer {self.customer_id} - {self.full_name}>"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "customer_id": self.customer_id,
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth,
            "address": self.address,
            "email": self.email,
            "phone": self.phone,
            "account_number": self.account_number,
            "account_type": self.account_type,
            "branch_code": self.branch_code,
        }


class Checker(Base):
    """
    Checker (reviewer) record.

    Tracks checker information and their permissions.
    """

    __tablename__ = "checkers"

    # ===================
    # Identity
    # ===================
    checker_id = Column(String(50), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)

    # ===================
    # Permissions
    # ===================
    is_senior = Column(String(5), default="false")  # Can handle HIGH risk requests
    is_active = Column(String(5), default="true")

    # ===================
    # Metadata
    # ===================
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Checker {self.checker_id} - {self.name}>"

    @property
    def can_handle_high_risk(self) -> bool:
        """Check if checker can handle HIGH risk requests."""
        return self.is_senior == "true"
