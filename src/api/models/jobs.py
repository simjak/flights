import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class JobStatus(str, Enum):
    """Job status enum."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PriceIndicator(str, Enum):
    """Price indicator enum."""

    LOW = "low"
    TYPICAL = "typical"
    HIGH = "high"


class Job(Base):
    """Job model for tracking search progress."""

    __tablename__ = "jobs"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
        init=False,
    )
    status: Mapped[JobStatus] = mapped_column(
        String(length=20),
        default=JobStatus.PENDING,
        nullable=False,
    )
    total_tasks: Mapped[int] = mapped_column(default=0, nullable=False)
    completed_tasks: Mapped[int] = mapped_column(default=0, nullable=False)
    found_flights: Mapped[int] = mapped_column(default=0, nullable=False)
    best_price: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        default=None,
    )
    last_checkpoint: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
        init=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
        init=False,
    )

    results: Mapped[list["FlightResult"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        default_factory=list,
    )


class FlightResult(Base):
    """Flight result model for storing search results."""

    __tablename__ = "flight_results"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    )
    departure_airport: Mapped[str] = mapped_column(String(3), nullable=False)
    destination_airport: Mapped[str] = mapped_column(String(3), nullable=False)
    outbound_date: Mapped[datetime] = mapped_column(nullable=False)
    return_date: Mapped[datetime] = mapped_column(nullable=False)
    price: Mapped[float] = mapped_column(nullable=False)
    airline: Mapped[str] = mapped_column(String(100), nullable=False)
    stops: Mapped[int] = mapped_column(nullable=False)
    duration: Mapped[str] = mapped_column(String(20), nullable=False)
    current_price_indicator: Mapped[PriceIndicator] = mapped_column(
        String(20),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
        init=False,
    )

    job: Mapped[Job] = relationship(
        back_populates="results",
        init=False,
    )
