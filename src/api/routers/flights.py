from fastapi import APIRouter, BackgroundTasks, HTTPException

from ..models.flights import FlightSearchRequest, FlightSearchResponse
from ..services.flights import search_flights_service

router = APIRouter(
    prefix="/flights",
    tags=["flights"],
)


@router.post(
    "/search",
    response_model=FlightSearchResponse,
    summary="Search for flights",
    description="Search for flights based on specified criteria",
)
async def search_flights(
    request: FlightSearchRequest,
    background_tasks: BackgroundTasks,
) -> FlightSearchResponse:
    """
    Search for flights based on the provided criteria.

    The search is performed asynchronously and can be interrupted by the client.
    Results are streamed back as they become available.
    """
    try:
        response = await search_flights_service(
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
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during flight search: {str(e)}",
        )
