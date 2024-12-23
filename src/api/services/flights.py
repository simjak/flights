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
                    min_duration_days=params.get("min_duration_days", 13),
                    max_duration_days=params.get("max_duration_days", 30),
                    max_price=params.get("max_price", float("inf")),
                    max_stops=params.get("max_stops"),
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

                    if params.get("max_price") is None or price <= params["max_price"]:
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
                        search_progress.update_best_price(price, flight_info)

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
    max_concurrent_searches: int = 3,
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

        # Calculate the latest possible start date based on end_date and min_duration_days
        latest_start_date = end_date - timedelta(days=min_duration_days or 13)
        if start_date > latest_start_date:
            raise HTTPException(
                status_code=400,
                detail=f"Start date too late for minimum duration of {min_duration_days} days before end date",
            )

        # Generate date combinations
        date_range = generate_date_range(
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(latest_start_date, datetime.min.time()),
        )

        # Initialize progress tracking
        progress = SearchProgress()

        # Calculate total tasks before starting searches
        total_combinations = len(departure_airports)
        if destination_airports:
            total_combinations *= len(destination_airports)
        total_combinations *= len(date_range)
        progress.total_tasks = total_combinations

        results = []
        last_error = None

        # Create semaphore for concurrent searches
        semaphore = asyncio.Semaphore(max_concurrent_searches)

        # Search for each combination
        async def search_with_semaphore(
            dep: str, dest: str, outbound_date: str
        ) -> None:
            async with semaphore:
                task_id = f"{dep}-{dest}-{outbound_date}"
                task_desc = f"Searching {dep} to {dest} on {outbound_date}"
                progress.add_current_search(task_id, task_desc)

                try:
                    # Calculate return date based on min_duration_days
                    return_date = (
                        datetime.strptime(outbound_date, "%Y-%m-%d")
                        + timedelta(days=min_duration_days or 13)
                    ).strftime("%Y-%m-%d")

                    # Skip if return date would be after end_date
                    if datetime.strptime(return_date, "%Y-%m-%d").date() > end_date:
                        logger.debug(
                            f"Skipping {outbound_date} as return date {return_date} would be after end date {end_date}"
                        )
                        return

                    flights = await search_flight_combination(
                        dep,
                        dest,
                        outbound_date,
                        return_date,
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
                        min_price_flight = next(
                            f for f in flight_results if f.price == min_price
                        )
                        progress.update_best_price(
                            min_price,
                            {
                                "departure_airport": min_price_flight.departure_airport,
                                "destination_airport": min_price_flight.destination_airport,
                                "outbound_date": min_price_flight.outbound_date,
                                "return_date": min_price_flight.return_date,
                                "airline": min_price_flight.airline,
                                "stops": min_price_flight.stops,
                                "duration": min_price_flight.duration,
                                "current_price_indicator": min_price_flight.current_price_indicator,
                            },
                        )
                except Exception as e:
                    nonlocal last_error
                    last_error = e
                finally:
                    progress.increment_completed()
                    progress.remove_current_search(task_id)

        # Create tasks for all combinations
        tasks = []
        for dep, dest in product(departure_airports, destination_airports or []):
            for outbound_date in date_range:
                tasks.append(search_with_semaphore(dep, dest, outbound_date))

        # Run all tasks concurrently
        await asyncio.gather(*tasks)

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
