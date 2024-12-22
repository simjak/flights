"""Flight search functionality."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from .core import get_flights
from .flights_impl import FlightData, create_filter
from .types import Passengers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def search_flights(
    departure_airports: List[str],
    destination_airports: List[str],
    start_date: str,
    end_date: str,
    min_duration_days: int = 13,
    max_duration_days: int = 30,
    max_price: float = 700.0,
    max_stops: Optional[int] = None,
    max_concurrent_searches: int = 3,
) -> List[dict]:
    """
    Search for flights based on multiple parameters.
    """
    # Validate dates
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        current = datetime.now()

        # Check if dates are too close to current date
        min_future_days = 7
        if (start - current).days < min_future_days:
            logger.error(
                f"Start date must be at least {min_future_days} days in the future"
            )
            return []

        # Check if dates are too far in the future
        max_future_days = 365 * 2
        if (start - current).days > max_future_days:
            logger.error(
                f"Start date cannot be more than {max_future_days // 365} years in the future"
            )
            return []

        # Check if end date is after start date
        if end < start:
            logger.error("End date must be after start date")
            return []

    except ValueError as e:
        logger.error(f"Invalid date format: {str(e)}")
        return []

    # Validate duration constraints
    if min_duration_days > max_duration_days:
        logger.error("Minimum duration cannot be greater than maximum duration")
        return []

    if min_duration_days < 1:
        logger.error("Minimum duration must be at least 1 day")
        return []

    if max_duration_days > 90:
        logger.error("Maximum duration cannot exceed 90 days")
        return []

    # Create semaphore to limit concurrent tasks
    semaphore = asyncio.Semaphore(max_concurrent_searches)

    async def search_combination(
        dep_airport: str,
        dest_airport: str,
        outbound_date: str,
        return_date: str,
    ) -> List[dict]:
        """Search for a specific flight combination."""
        async with semaphore:
            try:
                # Create flight filter
                filter = create_filter(
                    flight_data=[
                        FlightData(
                            date=outbound_date,
                            from_airport=dep_airport,
                            to_airport=dest_airport,
                        ),
                        FlightData(
                            date=return_date,
                            from_airport=dest_airport,
                            to_airport=dep_airport,
                        ),
                    ],
                    trip="round-trip",
                    seat="economy",
                    passengers=Passengers(adults=1),
                    max_stops=max_stops,
                )

                # Get flights
                result = await get_flights(filter, inject_eu_cookies=True)
                if not result or not result.flights:
                    return []

                # Process results
                found_flights = []
                for flight in result.flights:
                    # Extract price value
                    price_str = flight.price.replace("€", "").replace(",", "").strip()
                    try:
                        price = float(price_str)
                        if price <= max_price:
                            flight_info = {
                                "departure_airport": dep_airport,
                                "destination_airport": dest_airport,
                                "outbound_date": outbound_date,
                                "return_date": return_date,
                                "price": price,
                                "airline": flight.name,
                                "stops": flight.stops,
                                "duration": flight.duration,
                                "current_price_indicator": result.current_price,
                            }
                            found_flights.append(flight_info)
                    except ValueError:
                        continue

                return found_flights

            except Exception as e:
                logger.error(
                    f"Error searching {dep_airport} → {dest_airport}: {str(e)}"
                )
                return []

    # Generate all possible combinations
    tasks = []
    for dep_airport in departure_airports:
        for dest_airport in destination_airports:
            outbound = start_date
            return_date = (
                datetime.strptime(outbound, "%Y-%m-%d")
                + timedelta(days=min_duration_days)
            ).strftime("%Y-%m-%d")

            if return_date <= end_date:
                tasks.append(
                    search_combination(
                        dep_airport,
                        dest_airport,
                        outbound,
                        return_date,
                    )
                )

    # Execute all tasks
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"Error during flight search: {str(e)}")
        return []

    # Combine and sort results
    all_flights = []
    for result in results:
        if isinstance(result, list):
            all_flights.extend(result)

    return sorted(all_flights, key=lambda x: x["price"])
