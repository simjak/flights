import asyncio
from datetime import datetime, timedelta, date
from typing import List, Optional, Set

from fast_flights import (
    FlightData,
    Passengers,
    Result,
    create_filter,
    get_flights,
)

from ...api.db.service import DatabaseService
from ...api.models.jobs import FlightResult, Job
from ..utils.logger import get_logger
from .rate_limiter import RateLimiter
from .state import JobStatus, SearchCombination, StateManager

logger = get_logger(__name__)


class FlightSearchWorker:
    """Worker for processing flight search jobs."""

    def __init__(
        self,
        db_service: DatabaseService,
        concurrency_limit: int = 5,
        rate_limit: int = 60,
        time_window: int = 60,
        checkpoint_interval: int = 300,
    ):
        """
        Initialize flight search worker.

        Args:
            db_service: Database service instance
            concurrency_limit: Maximum number of concurrent searches
            rate_limit: Number of requests allowed per time window
            time_window: Time window in seconds
            checkpoint_interval: Interval between checkpoints in seconds
        """
        self.db_service = db_service
        self.concurrency_limit = concurrency_limit
        self.checkpoint_interval = checkpoint_interval
        self.rate_limiter = RateLimiter(rate_limit, time_window)
        self.state_manager = StateManager()
        self._running_tasks: Set[asyncio.Task] = set()
        self._checkpoint_task: Optional[asyncio.Task] = None

    async def start_job(self, job: Job) -> None:
        """
        Start processing a flight search job.

        Args:
            job: Job instance from database
        """
        logger.info(f"Starting job {job.job_id}")

        # Initialize job state
        state = self.state_manager.create_job(job.job_id)
        self.state_manager.update_job_status(job.job_id, JobStatus.RUNNING)

        # Generate search combinations
        combinations = self._generate_combinations(
            job.departure_airports,
            job.destination_airports,
            job.start_date,
            job.end_date,
            job.min_duration_days,
            job.max_duration_days,
        )

        # Add combinations to state
        for combination in combinations:
            state.add_combination(combination)

        logger.info(
            f"Job {job.job_id} initialized with {state.total_combinations} combinations"
        )

        # Start checkpoint task
        self._checkpoint_task = asyncio.create_task(self._checkpoint_loop(job.job_id))

        try:
            # Process combinations with controlled concurrency
            await self._process_combinations(job.job_id)
        except Exception as e:
            logger.error(f"Job {job.job_id} failed: {str(e)}")
            self.state_manager.update_job_status(job.job_id, JobStatus.FAILED)
            await self.db_service.update_job_status(job.job_id, "failed")
        else:
            logger.info(f"Job {job.job_id} completed")
            self.state_manager.update_job_status(job.job_id, JobStatus.COMPLETED)
            await self.db_service.update_job_status(job.job_id, "completed")
        finally:
            # Clean up
            if self._checkpoint_task:
                self._checkpoint_task.cancel()
            self.state_manager.cleanup_job(job.job_id)

    async def _process_combinations(self, job_id: str) -> None:
        """
        Process search combinations with controlled concurrency.

        Args:
            job_id: Job ID
        """
        state = self.state_manager.get_job(job_id)
        if not state:
            raise ValueError(f"Job {job_id} not found")

        while not state.is_complete():
            # Start new tasks up to concurrency limit
            while len(self._running_tasks) < self.concurrency_limit and (
                combination := state.get_next_combination()
            ):
                task = asyncio.create_task(
                    self._process_combination(job_id, combination)
                )
                self._running_tasks.add(task)
                task.add_done_callback(self._running_tasks.discard)

            if self._running_tasks:
                # Wait for at least one task to complete
                await asyncio.wait(
                    self._running_tasks, return_when=asyncio.FIRST_COMPLETED
                )
            else:
                # No tasks running and no combinations left
                break

    async def _process_combination(
        self,
        job_id: str,
        combination: SearchCombination,
    ) -> None:
        """
        Process a single search combination.

        Args:
            job_id: Job ID
            combination: Search combination to process
        """
        state = self.state_manager.get_job(job_id)
        if not state:
            raise ValueError(f"Job {job_id} not found")

        try:
            # Wait for rate limit
            await self.rate_limiter.acquire()

            # Create flight filter
            filter = create_filter(
                flight_data=[
                    FlightData(
                        date=combination.outbound_date.strftime("%Y-%m-%d"),
                        from_airport=combination.departure,
                        to_airport=combination.destination,
                    ),
                    FlightData(
                        date=combination.return_date.strftime("%Y-%m-%d"),
                        from_airport=combination.destination,
                        to_airport=combination.departure,
                    ),
                ],
                trip="round-trip",
                seat="economy",  # TODO: Make configurable
                passengers=Passengers(adults=1),
                max_stops=2,  # TODO: Use from job config
            )

            # Get flights with improved retry mechanism
            max_retries = 3
            retry_delay = 5  # Initial delay in seconds
            last_error = None
            result = None

            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        logger.debug(
                            f"Retry attempt {attempt + 1}/{max_retries} for {combination}"
                        )
                        await asyncio.sleep(retry_delay)

                    # Make request using async get_flights
                    result = await get_flights(filter, inject_eu_cookies=True)

                    # If we got flights, process them
                    if result and result.flights:
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
            if result and result.flights:
                for flight in result.flights:
                    # Extract price value (assuming EUR)
                    price_str = flight.price.replace("€", "").replace(",", "").strip()
                    try:
                        price = float(price_str)
                        # Save result to database
                        await self.db_service.create_flight_result(
                            job_id=job_id,
                            departure_airport=combination.departure,
                            destination_airport=combination.destination,
                            outbound_date=combination.outbound_date,
                            return_date=combination.return_date,
                            price=price,
                            airline=flight.name,
                            stops=flight.stops,
                            duration=flight.duration,
                            current_price_indicator=result.current_price,
                        )
                        logger.info(
                            f"Found flight: {combination.departure} → {combination.destination} "
                            f"({combination.outbound_date} - {combination.return_date}) "
                            f"€{price:.2f} with {flight.name}"
                        )
                    except ValueError:
                        logger.warning(f"Invalid price format: {flight.price}")
                        continue
            elif last_error:
                raise last_error
            else:
                logger.warning("No flights found after retries")

            # Mark combination as processed
            state.mark_combination_processed(combination)

        except Exception as e:
            logger.error(f"Failed to process combination {combination}: {str(e)}")
            state.mark_combination_processed(combination, error=str(e))

    async def _checkpoint_loop(self, job_id: str) -> None:
        """
        Periodically checkpoint job progress.

        Args:
            job_id: Job ID
        """
        while True:
            try:
                await asyncio.sleep(self.checkpoint_interval)
                state = self.state_manager.get_job(job_id)
                if not state:
                    break

                # Update checkpoint
                self.state_manager.checkpoint_job(job_id)

                # Update progress in database
                progress = state.get_progress()
                await self.db_service.update_job_status(
                    job_id,
                    status=state.status.value,
                    total_combinations=state.total_combinations,
                    processed_combinations=state.processed_combinations,
                    progress=progress,
                    last_checkpoint=datetime.utcnow(),
                )

                logger.debug(
                    f"Job {job_id} progress: {progress:.1f}% "
                    f"({state.processed_combinations}/{state.total_combinations})"
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Checkpoint error for job {job_id}: {str(e)}")

    @staticmethod
    def _generate_combinations(
        departure_airports: List[str],
        destination_airports: List[str],
        start_date: date,
        end_date: date,
        min_duration_days: int,
        max_duration_days: int,
    ) -> List[SearchCombination]:
        """
        Generate all possible search combinations.

        Args:
            departure_airports: List of departure airport codes
            destination_airports: List of destination airport codes
            start_date: Start date for search
            end_date: End date for search
            min_duration_days: Minimum duration of stay
            max_duration_days: Maximum duration of stay

        Returns:
            List of search combinations
        """
        combinations = []
        current_date = start_date
        while current_date <= end_date - timedelta(days=min_duration_days):
            for dep in departure_airports:
                for dest in destination_airports:
                    if dep == dest:
                        continue
                    # For each outbound date, try all possible return dates
                    # within the duration constraints
                    min_return_date = current_date + timedelta(days=min_duration_days)
                    max_return_date = min(
                        current_date + timedelta(days=max_duration_days),
                        end_date,
                    )
                    if min_return_date <= max_return_date:
                        combinations.append(
                            SearchCombination(
                                departure=dep,
                                destination=dest,
                                outbound_date=current_date,
                                return_date=min_return_date,
                            )
                        )
            current_date += timedelta(days=1)
        return combinations
