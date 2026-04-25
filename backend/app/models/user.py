"""
User Model for Authentication

Defines the User model with role-based access control.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func

from app.db.session import Base


class UserRole(str, Enum):
    """User roles for access control."""
    STAFF = "staff"
    CHECKER = "checker"
    ADMIN = "admin"


class User(Base):
    """
    User model for authentication and authorization.

    Attributes:
        id: Unique user identifier (e.g., USR-ABC12345)
        username: Login username (unique)
        email: User email (unique)
        password_hash: Bcrypt hashed password
        role: User role (staff, checker, admin)
        is_active: Whether user can log in
        checker_id: Link to Checker record for checker users
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        last_login: Last successful login timestamp
    """
    __tablename__ = "users"

    # ===================
    # Identity
    # ===================
    id = Column(String(50), primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # ===================
    # Authorization
    # ===================
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.STAFF)
    is_active = Column(Boolean, default=True, nullable=False)

    # Link to existing Checker record for checker role users
    checker_id = Column(String(50), nullable=True)

    # ===================
    # Metadata
    # ===================
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    last_login = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User {self.username} ({self.role.value})>"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "is_active": self.is_active,
            "checker_id": self.checker_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
