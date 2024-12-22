"""Utility classes and functions for flight search optimization."""

import logging
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple, TypeGuard, Union

from fast_flights import FlightData, Passengers, Result, create_filter, get_flights

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Constants
TIME_DECAY_FACTOR = 0.0001  # Controls how quickly search scores decay over time


class SearchOptimizer:
    """Optimizes the search order based on various heuristics."""

    def __init__(self):
        """Initialize the search optimizer."""
        self.search_history: Dict[str, Dict[str, Any]] = {}

    def optimize_search_order(
        self, combinations: List[Tuple[str, str, str]]
    ) -> List[Tuple[str, str, str]]:
        """Optimize the order of search combinations."""
        # Sort combinations based on historical success rate and price
        scored_combinations = [
            (self._score_combination(combo), combo) for combo in combinations
        ]
        scored_combinations.sort(key=lambda x: x[0], reverse=True)
        return [combo for _, combo in scored_combinations]

    def _score_combination(self, combination: Tuple[str, str, str]) -> float:
        """Score a combination based on historical data."""
        dep_airport, dest_airport, date = combination
        route_key = f"{dep_airport}-{dest_airport}"

        if route_key not in self.search_history:
            return 0.5  # Default score for unknown routes

        history = self.search_history[route_key]
        success_rate = history.get("success_rate", 0.5)
        avg_price = history.get("avg_price", float("inf"))
        last_search = history.get("last_search", datetime.min)

        # Calculate time decay factor (lower score for older searches)
        time_since_search = (datetime.now() - last_search).total_seconds()
        time_decay = 1.0 / (1.0 + TIME_DECAY_FACTOR * time_since_search)

        # Combine factors into final score
        price_factor = 1.0 / (
            1.0 + (avg_price or float("inf")) / 1000.0
        )  # Normalize price impact
        return success_rate * 0.4 + price_factor * 0.4 + time_decay * 0.2

    def record_success(
        self, dep_airport: str, dest_airport: str, price: Optional[float] = None
    ):
        """Record a successful search."""
        self.update_history(dep_airport, dest_airport, True, price)

    def record_failure(self, dep_airport: str, dest_airport: str):
        """Record a failed search."""
        self.update_history(dep_airport, dest_airport, False)

    def update_history(
        self,
        dep_airport: str,
        dest_airport: str,
        success: bool,
        price: Optional[float] = None,
    ):
        """Update search history with results."""
        route_key = f"{dep_airport}-{dest_airport}"
        if route_key not in self.search_history:
            self.search_history[route_key] = {
                "total_searches": 0,
                "successful_searches": 0,
                "total_price": 0,
                "success_rate": 0.0,
                "avg_price": None,
                "last_search": None,
            }

        history = self.search_history[route_key]
        history["total_searches"] += 1
        if success:
            history["successful_searches"] += 1
            if price is not None:
                history["total_price"] = (history["total_price"] or 0) + price

        history["success_rate"] = (
            history["successful_searches"] / history["total_searches"]
        )
        if price is not None and history["successful_searches"] > 0:
            history["avg_price"] = (
                history["total_price"] / history["successful_searches"]
            )
        history["last_search"] = datetime.now()


@lru_cache(maxsize=1000)
async def cached_get_flights(
    outbound_date: str,
    return_date: str,
    from_airport: str,
    to_airport: str,
    max_stops: Optional[int] = None,
) -> Optional[Result]:
    """Cache flight search results to avoid duplicate requests"""
    try:
        filter = create_filter(
            flight_data=[
                FlightData(
                    date=outbound_date,
                    from_airport=from_airport,
                    to_airport=to_airport,
                ),
                FlightData(
                    date=return_date,
                    from_airport=to_airport,
                    to_airport=from_airport,
                ),
            ],
            trip="round-trip",
            seat="economy",
            passengers=Passengers(adults=1),
            max_stops=max_stops,
        )
        result = await get_flights(filter, inject_eu_cookies=True)
        return result
    except Exception as e:
        logger.error(f"Error in cached_get_flights: {str(e)}")
        return None


def is_flight_list(result: Union[List[dict], BaseException]) -> TypeGuard[List[dict]]:
    """Type guard to check if result is a list of flight dictionaries"""
    return isinstance(result, list) and all(isinstance(item, dict) for item in result)


def generate_date_range(
    start_date: datetime,
    end_date: datetime,
    min_duration: Optional[int] = None,
    max_duration: Optional[int] = None,
) -> List[str]:
    """Generate a list of dates between start and end date."""
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates


def calculate_search_scope(
    departure_airports: List[str],
    destination_airports: List[str],
    start_date: str,
    end_date: str,
    min_duration: int,
    max_duration: int,
) -> Tuple[int, float]:
    """Calculate the total number of combinations and estimated search time."""
    # Convert dates to datetime objects
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    # Calculate number of days in search period
    days_in_period = (end - start).days + 1

    # Calculate possible outbound dates (accounting for return flight duration)
    possible_outbound_days = days_in_period - min_duration

    # Calculate average return dates per outbound date
    avg_return_dates = min(
        max_duration - min_duration + 1,
        days_in_period - min_duration,
    )

    # Calculate total combinations
    total_combinations = (
        len(departure_airports)
        * len(destination_airports)
        * possible_outbound_days
        * avg_return_dates
    )

    # Estimate search time (assuming 2 seconds per search)
    estimated_minutes = (total_combinations * 2) / 60

    return total_combinations, estimated_minutes
