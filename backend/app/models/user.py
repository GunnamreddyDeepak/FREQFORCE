import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.farmer import Farmer


class UserRole(str, enum.Enum):
    """Authoritative user roles defined in KISANQUEUE V2 architecture."""
    FARMER = "FARMER"
    CENTRE_OPERATOR = "CENTRE_OPERATOR"
    GOVERNMENT = "GOVERNMENT"


class User(Base):
    """User account model for authentication and role authorization.

    Supports passwordless OTP login using phone_number.
    Sensitive credentials and plaintext secrets are never stored.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        comment="Authoritative user UUID",
    )
    phone_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
        comment="Primary login phone number for OTP authentication",
    )
    role: Mapped[str] = mapped_column(
        String(32),
        default=UserRole.FARMER.value,
        nullable=False,
        index=True,
        comment="User role (FARMER, CENTRE_OPERATOR, GOVERNMENT)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active account flag",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Account creation timestamp (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Account last update timestamp (UTC)",
    )

    # 1-to-1 relationship with Farmer profile
    farmer: Mapped[Optional["Farmer"]] = relationship(
        "Farmer",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} role={self.role} is_active={self.is_active}>"
