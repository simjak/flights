from datetime import datetime
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.jobs import FlightResult, Job, JobStatus


class JobRepository:
    """Repository for job-related database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_job(self, total_tasks: int = 0) -> Job:
        """Create a new job."""
        job = Job(total_tasks=total_tasks)
        self.session.add(job)
        await self.session.commit()
        return job

    async def get_job(self, job_id: UUID) -> Optional[Job]:
        """Get a job by ID."""
        stmt = select(Job).where(Job.job_id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_job_status(
        self,
        job_id: UUID,
        status: JobStatus,
        completed_tasks: Optional[int] = None,
        found_flights: Optional[int] = None,
        best_price: Optional[float] = None,
        last_checkpoint: Optional[dict] = None,
    ) -> Optional[Job]:
        """Update job status and related fields."""
        job = await self.get_job(job_id)
        if not job:
            return None

        job.status = status
        if completed_tasks is not None:
            job.completed_tasks = completed_tasks
        if found_flights is not None:
            job.found_flights = found_flights
        if best_price is not None:
            job.best_price = best_price
        if last_checkpoint is not None:
            job.last_checkpoint = last_checkpoint
        job.updated_at = datetime.utcnow()

        await self.session.commit()
        return job

    async def add_flight_result(
        self,
        job_id: UUID,
        flight_result: dict,
    ) -> FlightResult:
        """Add a flight result to a job."""
        result = FlightResult(job_id=job_id, **flight_result)
        self.session.add(result)
        await self.session.commit()
        return result

    async def get_job_results(
        self,
        job_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[FlightResult]:
        """Get flight results for a job."""
        stmt = (
            select(FlightResult)
            .where(FlightResult.job_id == job_id)
            .order_by(FlightResult.price)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_pending_jobs(self) -> Sequence[Job]:
        """Get all pending jobs."""
        stmt = select(Job).where(Job.status == JobStatus.PENDING)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_running_jobs(self) -> Sequence[Job]:
        """Get all running jobs."""
        stmt = select(Job).where(Job.status == JobStatus.RUNNING)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_job(self, job_id: UUID) -> bool:
        """Delete a job and all its results."""
        job = await self.get_job(job_id)
        if not job:
            return False

        await self.session.delete(job)
        await self.session.commit()
        return True
