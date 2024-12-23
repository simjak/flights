from datetime import datetime, timedelta, date
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from worker.utils.logger import get_logger
from ..models.jobs import FlightResult, Job, JobStatus

logger = get_logger(__name__)


class DatabaseService:
    """Database service for handling database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize database service."""
        self.session = session

    async def create_job(
        self,
        departure_airports: list[str],
        destination_airports: list[str],
        start_date: date,
        end_date: date,
        min_duration_days: int = 13,
        max_duration_days: int = 30,
        max_price: float = 700.0,
        max_stops: int = 2,
        max_concurrent_searches: int = 3,
    ) -> Job:
        """Create a new job."""
        job = Job(
            departure_airports=departure_airports,
            destination_airports=destination_airports,
            start_date=start_date,
            end_date=end_date,
            min_duration_days=min_duration_days,
            max_duration_days=max_duration_days,
            max_price=max_price,
            max_stops=max_stops,
            max_concurrent_searches=max_concurrent_searches,
            status=JobStatus.PENDING,
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_job(self, job_id: UUID) -> Job | None:
        """Get a job by ID."""
        stmt = select(Job).where(Job.job_id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_job_status(
        self,
        job_id: UUID,
        status: str,
        total_combinations: int | None = None,
        processed_combinations: int | None = None,
        progress: float | None = None,
        last_checkpoint: datetime | None = None,
    ) -> Job | None:
        """Update job status."""
        stmt = (
            update(Job)
            .where(Job.job_id == job_id)
            .values(
                status=status,
                total_combinations=total_combinations
                if total_combinations is not None
                else Job.total_combinations,
                processed_combinations=processed_combinations
                if processed_combinations is not None
                else Job.processed_combinations,
                progress=progress if progress is not None else Job.progress,
                last_checkpoint=last_checkpoint
                if last_checkpoint is not None
                else Job.last_checkpoint,
            )
            .returning(Job)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def create_flight_result(
        self,
        job_id: UUID,
        departure_airport: str,
        destination_airport: str,
        outbound_date: date,
        return_date: date | None,
        price: float,
        airline: str,
        stops: int,
        duration: str,
        current_price_indicator: str,
    ) -> FlightResult:
        """Create a new flight result."""
        result = FlightResult(
            job_id=job_id,
            departure_airport=departure_airport,
            destination_airport=destination_airport,
            outbound_date=outbound_date,
            return_date=return_date,
            price=price,
            airline=airline,
            stops=stops,
            duration=duration,
            current_price_indicator=current_price_indicator,
        )
        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return result

    async def get_job_results(
        self,
        job_id: UUID,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[FlightResult]:
        """Get results for a job."""
        stmt = select(FlightResult).where(FlightResult.job_id == job_id)
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def cleanup_old_jobs(self, days: int = 7) -> None:
        """
        Clean up old completed jobs.

        Args:
            days: Number of days to keep jobs for
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(Job)
            .where(Job.created_at < cutoff)
            .where(Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED]))
        )
        result = await self.session.execute(stmt)
        old_jobs = list(result.scalars().all())

        for job in old_jobs:
            await self.session.delete(job)

        await self.session.commit()
        logger.info(f"Cleaned up {len(old_jobs)} old jobs")
