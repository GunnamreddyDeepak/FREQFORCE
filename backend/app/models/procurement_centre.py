import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class ProcurementCentre(Base):
    """Procurement-centre master data and spatial location."""

    __tablename__ = "procurement_centres"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        comment="Authoritative procurement centre UUID",
    )

    centre_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique procurement centre code",
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Procurement centre name",
    )

    address: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Centre address",
    )

    district: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
        comment="District",
    )

    state: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
        comment="State",
    )

    location: Mapped[object] = mapped_column(
        Geometry(
            geometry_type="POINT",
            srid=4326,
            spatial_index=False,
        ),
        nullable=False,
        comment="Centre geographic location in WGS84",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Centre active flag",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ProcurementCentre "
            f"id={self.id} code={self.centre_code}>"
        )