import asyncio
import logging
from datetime import date
from typing import List, Optional

from fast_flights import search_flights

from ..models.flights import FlightResult, FlightSearchResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default South Asian airports
SOUTH_ASIA_AIRPORTS = [
    "SIN",  # Singapore
    "BKK",  # Bangkok
    "KUL",  # Kuala Lumpur
    "CGK",  # Jakarta
    "MNL",  # Manila
    "SGN",  # Ho Chi Minh City
    "HAN",  # Hanoi
    "RGN",  # Yangon
    "PNH",  # Phnom Penh
    "DAD",  # Da Nang
]


async def search_flights_service(
    departure_airports: List[str],
    start_date: date,
    end_date: date,
    destination_airports: Optional[List[str]] = None,
    min_duration_days: int = 13,
    max_duration_days: int = 30,
    max_price: float = 700.0,
    max_stops: Optional[int] = 2,
    max_concurrent_searches: int = 3,
) -> FlightSearchResponse:
    """Service function to search for flights"""
    try:
        # Use default airports if none provided
        dest_airports = destination_airports or SOUTH_ASIA_AIRPORTS

        # Convert dates to strings
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        # Perform the search
        results = await search_flights(
            departure_airports=departure_airports,
            destination_airports=dest_airports,
            start_date=start_date_str,
            end_date=end_date_str,
            min_duration_days=min_duration_days,
            max_duration_days=max_duration_days,
            max_price=max_price,
            max_stops=max_stops,
            max_concurrent_searches=max_concurrent_searches,
        )

        # Convert results to response model
        flight_results = [
            FlightResult(
                departure_airport=result["departure_airport"],
                destination_airport=result["destination_airport"],
                outbound_date=result["outbound_date"],
                return_date=result["return_date"],
                price=result["price"],
                airline=result["airline"],
                stops=result["stops"],
                duration=result["duration"],
                current_price_indicator=result["current_price_indicator"],
            )
            for result in results
        ]

        # Sort results by price
        flight_results.sort(key=lambda x: x.price)

        # Create response
        response = FlightSearchResponse(
            total_results=len(flight_results),
            best_price=min(r.price for r in flight_results) if flight_results else None,
            results=flight_results,
            search_status="completed",
        )

        return response

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Search interrupted by user")
        return FlightSearchResponse(
            total_results=0,
            best_price=None,
            results=[],
            search_status="interrupted",
        )
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise
