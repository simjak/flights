"""Flight search service with optimization and anti-blocking features."""

import asyncio
import logging
from datetime import date, datetime, timedelta
from itertools import product
from typing import List, Optional

from fastapi import HTTPException

from fast_flights import search_flights

from ..models.flights import FlightResult, FlightSearchResponse, SearchProgress
from .search_utils import (
    SearchOptimizer,
    generate_date_range,
)

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

# Global instances
search_progress = SearchProgress()
search_optimizer = SearchOptimizer()


async def search_flight_combination(
    dep_airport: str,
    dest_airport: str,
    outbound_date: str,
    return_date: str,
    params: dict,
) -> List[dict]:
    """Search for flights for a specific combination of parameters"""
    found_flights = []

    # Create unique task ID and description
    task_id = f"{dep_airport}-{dest_airport}-{outbound_date}-{return_date}"
    task_description = (
        f"{dep_airport} → {dest_airport} ({outbound_date} - {return_date})"
    )

    try:
        # Update current searches
        search_progress.add_current_search(task_id, task_description)
        logger.info(f"Searching: {task_description}")

        # Get flights with improved retry mechanism
        max_retries = 3
        retry_delay = 5  # Initial delay in seconds
        last_error = None
        result = None

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.debug(
                        f"Retry attempt {attempt + 1}/{max_retries} for {task_description}"
                    )
                    await asyncio.sleep(retry_delay)

                # Make request using async get_flights
                result = await search_flights(
                    departure_airports=[dep_airport],
                    destination_airports=[dest_airport],
                    start_date=outbound_date,
                    end_date=return_date,
                    min_duration_days=params["min_duration_days"],
                    max_duration_days=params["max_duration_days"],
                    max_price=params["max_price"],
                    max_stops=params["max_stops"],
                    max_concurrent_searches=1,  # Use 1 since we're already parallelizing
                )

                # If we got flights, process them
                if result and len(result) > 0:
                    break

                # If no flights found but request was successful, wait before retry
                retry_delay = min(retry_delay * 2, 30)  # Exponential backoff, max 30s
                logger.debug(
                    f"No flights found on attempt {attempt + 1}/{max_retries}, waiting {retry_delay}s"
                )

            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                retry_delay = min(retry_delay * 2, 30)
                continue

        # Process results if we found any flights
        if result and len(result) > 0:
            for flight in result:
                try:
                    # Handle both string and float price values
                    price = (
                        float(flight["price"].replace("€", "").replace(",", "").strip())
                        if isinstance(flight["price"], str)
                        else float(flight["price"])
                    )

                    if price <= params["max_price"]:
                        flight_info = {
                            "departure_airport": dep_airport,
                            "destination_airport": dest_airport,
                            "outbound_date": outbound_date,
                            "return_date": return_date,
                            "price": price,
                            "airline": flight["airline"],
                            "stops": flight["stops"],
                            "duration": flight["duration"],
                            "current_price_indicator": flight[
                                "current_price_indicator"
                            ],
                        }
                        found_flights.append(flight_info)

                        # Update progress
                        search_progress.increment_found_flights()
                        search_progress.update_best_price(price)

                        # Log new flight found
                        logger.info(
                            f"Found flight: {dep_airport} → {dest_airport} "
                            f"({outbound_date} - {return_date}) "
                            f"€{price:.2f} with {flight['airline']}"
                        )
                except (ValueError, KeyError, TypeError) as e:
                    logger.warning(f"Error processing flight price: {str(e)}")
                    continue

            # Record successful search if we found flights
            search_optimizer.record_success(dep_airport, dest_airport)
        elif last_error:
            # If we had an error and no results, raise it
            search_optimizer.record_failure(dep_airport, dest_airport)
            raise HTTPException(
                status_code=500,
                detail=f"Error searching flights: {str(last_error)}",
            )
        else:
            search_optimizer.record_failure(dep_airport, dest_airport)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching {task_description}: {str(e)}")
        search_optimizer.record_failure(dep_airport, dest_airport)
        raise HTTPException(
            status_code=500,
            detail=f"Error searching flights: {str(e)}",
        )
    finally:
        # Update progress
        search_progress.increment_completed()
        search_progress.remove_current_search(task_id)

        # Log progress
        logger.info(
            f"Progress: {search_progress.completed_tasks}/{search_progress.total_tasks} tasks completed, {search_progress.found_flights} flights found"
        )

    return found_flights


async def search_flights_service(
    departure_airports: List[str],
    destination_airports: Optional[List[str]] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    min_duration_days: Optional[int] = None,
    max_duration_days: Optional[int] = None,
    max_price: Optional[float] = None,
    max_stops: Optional[int] = None,
) -> FlightSearchResponse:
    """Search for flights based on given parameters."""
    try:
        # Validate dates
        current_date = datetime.now().date()
        min_start_date = current_date + timedelta(days=7)

        if not start_date:
            start_date = min_start_date
        if not end_date:
            end_date = start_date + timedelta(days=30)  # Default 30-day search window

        if start_date < min_start_date:
            raise HTTPException(
                status_code=400,
                detail=f"Start date must be at least 7 days in the future (minimum: {min_start_date})",
            )

        if (
            min_duration_days
            and max_duration_days
            and min_duration_days > max_duration_days
        ):
            raise HTTPException(
                status_code=400,
                detail="Minimum duration cannot be greater than maximum duration",
            )

        if (end_date - start_date).days < (min_duration_days or 0):
            raise HTTPException(
                status_code=400,
                detail=f"Date range too short for minimum duration of {min_duration_days} days",
            )

        # Initialize progress tracking
        progress = SearchProgress()

        # Generate date combinations
        date_range = generate_date_range(
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(end_date, datetime.min.time()),
        )
        total_combinations = (
            len(departure_airports) * len(destination_airports or []) * len(date_range)
        )
        progress.total_tasks = total_combinations

        results = []
        last_error = None

        # Search for each combination
        for dep, dest in product(departure_airports, destination_airports or []):
            for outbound_date in date_range:
                task_id = f"{dep}-{dest}-{outbound_date}"
                task_desc = f"Searching {dep} to {dest} on {outbound_date}"
                progress.add_current_search(task_id, task_desc)

                try:
                    flights = await search_flight_combination(
                        dep,
                        dest,
                        outbound_date,
                        (
                            datetime.strptime(outbound_date, "%Y-%m-%d")
                            + timedelta(days=min_duration_days or 13)
                        ).strftime("%Y-%m-%d"),
                        {
                            "max_price": max_price,
                            "min_duration_days": min_duration_days,
                            "max_duration_days": max_duration_days,
                            "max_stops": max_stops,
                        },
                    )
                    if flights:
                        # Convert flights to FlightResult objects
                        flight_results = [
                            FlightResult(
                                departure_airport=flight["departure_airport"],
                                destination_airport=flight["destination_airport"],
                                outbound_date=flight["outbound_date"],
                                return_date=flight["return_date"],
                                price=float(flight["price"])
                                if isinstance(flight["price"], str)
                                else flight["price"],
                                airline=flight["airline"],
                                stops=flight["stops"],
                                duration=flight["duration"],
                                current_price_indicator=flight[
                                    "current_price_indicator"
                                ],
                            )
                            for flight in flights
                        ]
                        results.extend(flight_results)
                        progress.increment_found_flights()
                        min_price = min(float(f.price) for f in flight_results)
                        progress.update_best_price(min_price)
                except Exception as e:
                    last_error = e
                finally:
                    progress.increment_completed()
                    progress.remove_current_search(task_id)

        if not results and last_error:
            raise HTTPException(
                status_code=500,
                detail=f"Error searching flights: {str(last_error)}",
            )

        return FlightSearchResponse(
            total_results=len(results),
            best_price=progress.best_price,
            results=results,
            search_status="completed",
            progress=progress,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching flights: {str(e)}",
        )
