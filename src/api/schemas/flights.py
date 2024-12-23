from datetime import datetime, date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class FlightSearchRequest(BaseModel):
    """Flight search request schema."""

    departure_airports: List[str] = Field(
        ...,
        min_length=1,
        description="List of departure airport codes",
        examples=["VNO", "RIX"],
    )
    destination_airports: List[str] = Field(
        ...,
        min_length=1,
        description="List of destination airport codes",
        examples=["SIN", "BKK"],
    )
    start_date: date = Field(
        ...,
        description="Start date for the search period",
        examples=["2025-02-01"],
    )
    end_date: date = Field(
        ...,
        description="End date for the search period",
        examples=["2025-02-15"],
    )
    min_duration_days: int = Field(
        13,
        description="Minimum duration of stay in days",
        ge=1,
        le=90,
    )
    max_duration_days: int = Field(
        30,
        description="Maximum duration of stay in days",
        ge=1,
        le=90,
    )
    max_price: float = Field(
        700.0,
        description="Maximum price in EUR",
        gt=0,
    )
    max_stops: int = Field(
        2,
        description="Maximum number of stops",
        ge=0,
        le=3,
    )
    max_concurrent_searches: int = Field(
        3,
        description="Maximum number of concurrent searches",
        ge=1,
        le=5,
    )


class JobResponse(BaseModel):
    """Job response schema."""

    job_id: UUID = Field(..., description="Job ID")
    status: str = Field(..., description="Job status")
    total_combinations: int = Field(..., description="Total number of combinations")
    processed_combinations: int = Field(
        ...,
        description="Number of processed combinations",
    )
    progress: float = Field(..., description="Progress percentage")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: datetime = Field(..., description="Job last update timestamp")


class JobStatusResponse(JobResponse):
    """Job status response schema."""

    last_checkpoint: Optional[datetime] = Field(
        None,
        description="Last checkpoint timestamp",
    )


class FlightResultResponse(BaseModel):
    """Flight result response schema."""

    id: UUID = Field(..., description="Result ID")
    job_id: UUID = Field(..., description="Job ID")
    departure_airport: str = Field(..., description="Departure airport code")
    destination_airport: str = Field(..., description="Destination airport code")
    outbound_date: datetime = Field(..., description="Outbound date")
    return_date: Optional[datetime] = Field(None, description="Return date")
    price: float = Field(..., description="Flight price")
    airline: str = Field(..., description="Airline name")
    stops: int = Field(..., description="Number of stops")
    duration: str = Field(..., description="Flight duration in HH:MM format")
    current_price_indicator: str = Field(
        ...,
        description="Price indicator (low/typical/high)",
    )
    created_at: datetime = Field(..., description="Result creation timestamp")
