from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from worker.queue import TaskMessage, TaskQueue
from api.db.service import DatabaseService
from api.db.session import get_session
from api.schemas.flights import (
    FlightResultResponse,
    FlightSearchRequest,
    JobResponse,
    JobStatusResponse,
)

router = APIRouter()


@router.post("/search", response_model=JobResponse)
async def search_flights(
    request: FlightSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> JobResponse:
    """
    Start a new flight search job.

    Args:
        request: Flight search request parameters
        session: Database session

    Returns:
        Created job details
    """
    # Create job in database
    db = DatabaseService(session)
    job = await db.create_job(
        departure_airports=request.departure_airports,
        destination_airports=request.destination_airports,
        start_date=request.start_date,
        end_date=request.end_date,
        min_duration_days=request.min_duration_days,
        max_duration_days=request.max_duration_days,
        max_price=request.max_price,
        max_stops=request.max_stops,
        max_concurrent_searches=request.max_concurrent_searches,
    )

    # Create task message
    message = TaskMessage(
        job_id=job.job_id,
        task_type="flight_search",
        payload={
            "departure_airports": request.departure_airports,
            "destination_airports": request.destination_airports,
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "min_duration_days": request.min_duration_days,
            "max_duration_days": request.max_duration_days,
            "max_price": request.max_price,
            "max_stops": request.max_stops,
            "max_concurrent_searches": request.max_concurrent_searches,
        },
    )

    # Send task to queue
    async with TaskQueue() as queue:
        await queue.enqueue(message)

    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        total_combinations=job.total_combinations,
        processed_combinations=job.processed_combinations,
        progress=job.progress,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> JobStatusResponse:
    """
    Get job status.

    Args:
        job_id: Job ID
        session: Database session

    Returns:
        Job status details
    """
    db = DatabaseService(session)
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        total_combinations=job.total_combinations,
        processed_combinations=job.processed_combinations,
        progress=job.progress,
        last_checkpoint=job.last_checkpoint,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/jobs/{job_id}/results", response_model=List[FlightResultResponse])
async def get_job_results(
    job_id: UUID,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
) -> List[FlightResultResponse]:
    """
    Get job results.

    Args:
        job_id: Job ID
        limit: Maximum number of results to return
        offset: Number of results to skip
        session: Database session

    Returns:
        List of flight results
    """
    db = DatabaseService(session)
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    results = await db.get_job_results(job_id, limit=limit, offset=offset)
    return [
        FlightResultResponse(
            id=result.id,
            job_id=result.job_id,
            departure_airport=result.departure_airport,
            destination_airport=result.destination_airport,
            outbound_date=result.outbound_date,
            return_date=result.return_date,
            price=result.price,
            airline=result.airline,
            stops=result.stops,
            duration=result.duration,
            current_price_indicator=result.current_price_indicator,
            created_at=result.created_at,
        )
        for result in results
    ]
