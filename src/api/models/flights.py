import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


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
        description="Start date for the search period (must be at least 7 days in the future)",
        json_schema_extra={"examples": ["2025-02-01"]},
    )
    end_date: date = Field(
        ...,
        description="End date for the search period",
        json_schema_extra={"examples": ["2025-02-15"]},
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

    @field_validator("start_date")
    @classmethod
    def validate_start_date(cls, v: date) -> date:
        """Validate that start_date is at least 7 days in the future"""
        today = datetime.now().date()
        min_date = today + timedelta(days=7)
        logger.info(f"Today: {today}, Min allowed date: {min_date}, Provided date: {v}")
        if v < min_date:
            raise ValueError(
                f"Start date must be at least 7 days in the future (no earlier than {min_date})"
            )
        return v

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


class SearchProgress(BaseModel):
    """Model for tracking search progress."""

    total_tasks: int = Field(default=0, description="Total number of search tasks")
    completed_tasks: int = Field(default=0, description="Number of completed tasks")
    found_flights: int = Field(default=0, description="Number of found flights")
    best_price: Optional[float] = Field(
        default=None, description="Best price found so far"
    )
    best_flight_details: Optional[Dict[str, Union[str, int]]] = Field(
        default=None, description="Details of the flight with the best price"
    )
    current_searches: Dict[str, str] = Field(
        default_factory=dict, description="Current active searches"
    )

    def add_current_search(self, task_id: str, description: str):
        """Add a search task to the current searches."""
        self.current_searches[task_id] = description

    def remove_current_search(self, task_id: str):
        """Remove a search task from the current searches."""
        self.current_searches.pop(task_id, None)

    def increment_found_flights(self):
        """Increment the number of found flights."""
        self.found_flights += 1
        logger.info(f"Found flights: {self.found_flights}")

    def increment_completed(self):
        """Increment the number of completed tasks."""
        self.completed_tasks += 1
        logger.info(
            f"Progress: {self.completed_tasks}/{self.total_tasks} tasks completed, {self.found_flights} flights found"
        )

    def update_best_price(
        self, price: float, flight_details: Dict[str, Union[str, int]]
    ):
        """Update the best price if lower than current."""
        if self.best_price is None or price < self.best_price:
            self.best_price = price
            self.best_flight_details = flight_details
            logger.info(
                f"New best price: €{self.best_price:.2f} - "
                f"{flight_details['departure_airport']} → {flight_details['destination_airport']} "
                f"({flight_details['outbound_date']} - {flight_details['return_date']}) "
                f"with {flight_details['airline']}, {flight_details['stops']} stops"
            )

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


class FlightResult(BaseModel):
    """Model for a single flight result."""

    departure_airport: str
    destination_airport: str
    outbound_date: str
    return_date: str
    price: float
    airline: str
    stops: int
    duration: str
    current_price_indicator: str

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


class FlightSearchResponse(BaseModel):
    """Model for flight search response."""

    total_results: int
    best_price: Optional[float]
    results: List[FlightResult]
    search_status: str
    progress: Optional[SearchProgress] = None

    class Config:
        """Pydantic model configuration."""

        from_attributes = True
