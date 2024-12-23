from datetime import datetime, date
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, Integer, String, Date
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PriceIndicator(str, Enum):
    """Price indicator enum."""

    LOW = "low"
    TYPICAL = "typical"
    HIGH = "high"


class JobStatus(str, Enum):
    """Job status enum."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base):
    """Flight search job model."""

    __tablename__ = "jobs"

    # Required fields without defaults
    departure_airports: Mapped[List[str]] = mapped_column(ARRAY(String))
    destination_airports: Mapped[List[str]] = mapped_column(ARRAY(String))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    min_duration_days: Mapped[int] = mapped_column(Integer, default=13)
    max_duration_days: Mapped[int] = mapped_column(Integer, default=30)
    max_price: Mapped[float] = mapped_column(Float, default=700.0)
    max_stops: Mapped[int] = mapped_column(Integer, default=2)
    max_concurrent_searches: Mapped[int] = mapped_column(Integer, default=3)

    # Optional fields
    last_checkpoint: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
    )

    # Fields with default values
    job_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    status: Mapped[str] = mapped_column(
        SQLEnum(JobStatus, values_callable=lambda x: [e.value for e in x]),
        default=JobStatus.PENDING,
    )
    total_combinations: Mapped[int] = mapped_column(Integer, default=0)
    processed_combinations: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class FlightResult(Base):
    """Flight search result model."""

    __tablename__ = "flight_results"

    # Required fields without defaults
    job_id: Mapped[UUID] = mapped_column(nullable=False)
    departure_airport: Mapped[str] = mapped_column(String(3), nullable=False)
    destination_airport: Mapped[str] = mapped_column(String(3), nullable=False)
    outbound_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    airline: Mapped[str] = mapped_column(String(100), nullable=False)
    stops: Mapped[int] = mapped_column(Integer, nullable=False)
    duration: Mapped[str] = mapped_column(String(20), nullable=False)  # Format: "HH:MM"
    current_price_indicator: Mapped[str] = mapped_column(
        SQLEnum(PriceIndicator),
        nullable=False,
    )

    # Optional fields
    return_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
    )

    # Fields with default values
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
