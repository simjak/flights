from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class FlightSearchRequest(BaseModel):
    """Request model for flight search"""

    departure_airports: List[str] = Field(
        ...,
        description="List of departure airport codes",
        json_schema_extra={"examples": ["VNO", "RIX", "WAW"]},
    )
    destination_airports: Optional[List[str]] = Field(
        None,
        description="List of destination airport codes. If not provided, defaults to South Asian airports",
        json_schema_extra={"examples": ["SIN", "BKK", "KUL"]},
    )
    start_date: date = Field(
        ...,
        description="Start date for the search period",
        json_schema_extra={"examples": ["2025-02-01"]},
    )
    end_date: date = Field(
        ...,
        description="End date for the search period",
        json_schema_extra={"examples": ["2025-04-30"]},
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
    max_stops: Optional[int] = Field(
        2,
        description="Maximum number of stops",
        ge=0,
        le=3,
    )
    max_concurrent_searches: Optional[int] = Field(
        3,
        description="Maximum number of concurrent searches",
        ge=1,
        le=5,
    )

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v: date, info) -> date:
        """Validate that end_date is after start_date"""
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v

    @field_validator("max_duration_days")
    @classmethod
    def validate_duration(cls, v: int, info) -> int:
        """Validate that max_duration_days is greater than min_duration_days"""
        if "min_duration_days" in info.data and v < info.data["min_duration_days"]:
            raise ValueError("max_duration_days must be greater than min_duration_days")
        return v


class FlightResult(BaseModel):
    """Model for a single flight result"""

    departure_airport: str = Field(description="Departure airport code")
    destination_airport: str = Field(description="Destination airport code")
    outbound_date: date = Field(description="Outbound flight date")
    return_date: date = Field(description="Return flight date")
    price: float = Field(description="Flight price in EUR")
    airline: str = Field(description="Airline name")
    stops: int = Field(description="Number of stops")
    duration: str = Field(description="Flight duration")
    current_price_indicator: str = Field(
        description="Price indicator (low/typical/high)",
    )


class FlightSearchResponse(BaseModel):
    """Response model for flight search"""

    total_results: int = Field(description="Total number of flights found")
    best_price: Optional[float] = Field(None, description="Best price found in EUR")
    results: List[FlightResult] = Field(description="List of flight results")
    search_status: str = Field(
        description="Status of the search (completed/interrupted)",
    )
