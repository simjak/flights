from datetime import date, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from api.models.flights import FlightSearchResponse
from api.services.flights import (
    SearchProgress,
    search_flight_combination,
    search_flights_service,
    search_progress,
)


@pytest.fixture(autouse=True)
def mock_retry_delay():
    """Mock retry delay to speed up tests."""
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        yield mock_sleep


@pytest.fixture(autouse=True)
def reset_search_progress():
    """Reset search progress before each test."""
    search_progress.total_tasks = 0
    search_progress.completed_tasks = 0
    search_progress.found_flights = 0
    search_progress.current_searches.clear()
    search_progress.best_price = None
    yield


@pytest.fixture
def mock_flights():
    return [
        {
            "departure_airport": "HEL",
            "destination_airport": "BKK",
            "outbound_date": "2024-02-01",
            "return_date": "2024-02-15",
            "price": "450.00",
            "airline": "Finnair",
            "stops": 1,
            "duration": "12h 30m",
            "current_price_indicator": "low",
        },
        {
            "departure_airport": "HEL",
            "destination_airport": "BKK",
            "outbound_date": "2024-02-02",
            "return_date": "2024-02-16",
            "price": 550.0,
            "airline": "Qatar Airways",
            "stops": 1,
            "duration": "13h 45m",
            "current_price_indicator": "typical",
        },
    ]


@pytest.fixture
def mock_search():
    with patch("api.services.flights.search_flights") as mock:
        yield mock


@pytest.fixture
def mock_datetime():
    """Mock datetime to return fixed values"""
    with patch("api.services.flights.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 1)
        mock_dt.combine = datetime.combine
        mock_dt.min = MagicMock()
        mock_dt.min.time.return_value = time(0, 0)
        mock_dt.strptime = datetime.strptime
        yield mock_dt


@pytest.mark.asyncio(scope="function")
async def test_search_flights_success(mock_flights, mock_search, mock_datetime):
    """Test successful flight search."""
    # Mock search parameters
    departure_airports = ["HEL"]
    destination_airports = ["BKK"]
    start_date = date(2024, 2, 1)
    end_date = date(2024, 2, 28)
    max_price = 1000.0

    # Mock search function to return different flights for each date
    mock_search.side_effect = [
        mock_flights[:1],
        mock_flights[1:],
    ]  # Split mock flights between dates

    # Mock date range generation
    with patch("api.services.flights.generate_date_range") as mock_date_range:
        mock_date_range.return_value = ["2024-02-01", "2024-02-02"]

        # Call service
        response = await search_flights_service(
            departure_airports=departure_airports,
            destination_airports=destination_airports,
            start_date=start_date,
            end_date=end_date,
            max_price=max_price,
        )

    # Verify response
    assert isinstance(response, FlightSearchResponse)
    assert response.total_results == len(mock_flights)
    assert response.best_price == 450.0
    assert len(response.results) == len(mock_flights)
    assert response.search_status == "completed"


@pytest.mark.asyncio(scope="function")
async def test_search_flights_validation():
    """Test input validation for flight search."""
    # Test invalid date (too soon)
    with pytest.raises(HTTPException) as exc_info:
        current = datetime.now()
        await search_flights_service(
            departure_airports=["HEL"],
            start_date=current.date(),
            end_date=current.date() + timedelta(days=30),
        )
    assert exc_info.value.status_code == 400
    assert "must be at least" in str(exc_info.value.detail)

    # Test invalid duration
    with patch("api.services.flights.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 1, 1)
        mock_datetime.combine = datetime.combine
        mock_datetime.min = MagicMock()
        mock_datetime.min.time.return_value = time(0, 0)
        mock_datetime.strptime = datetime.strptime

        with pytest.raises(HTTPException) as exc_info:
            await search_flights_service(
                departure_airports=["HEL"],
                start_date=date(2024, 2, 1),
                end_date=date(2024, 2, 10),
                min_duration_days=13,
            )
        assert exc_info.value.status_code == 400
        assert "too short" in str(exc_info.value.detail)


@pytest.mark.asyncio(scope="function")
async def test_search_flights_error_handling(mock_search, mock_datetime):
    """Test error handling in flight search."""
    # Mock search parameters
    departure_airports = ["XXX"]  # Invalid airport
    start_date = date(2024, 2, 1)
    end_date = date(2024, 2, 28)

    # Mock search to raise an error
    mock_search.side_effect = Exception("Invalid airport code")

    # Mock date range generation
    with patch("api.services.flights.generate_date_range") as mock_date_range:
        mock_date_range.return_value = ["2024-02-01"]

        # Test service error handling
        with pytest.raises(HTTPException) as exc_info:
            await search_flights_service(
                departure_airports=departure_airports,
                destination_airports=["YYY"],
                start_date=start_date,
                end_date=end_date,
            )
        assert exc_info.value.status_code == 500
        assert "Error searching flights" in str(exc_info.value.detail)


@pytest.mark.asyncio(scope="function")
async def test_price_parsing(mock_search, mock_datetime):
    """Test price parsing logic."""
    test_cases = [
        ("€450.00", 450.0),
        ("550.0", 550.0),
        ("1,234.56", 1234.56),
        (789.01, 789.01),
    ]

    # Mock date range generation
    with patch("api.services.flights.generate_date_range") as mock_date_range:
        mock_date_range.return_value = ["2024-02-01"]

        for price_input, expected_price in test_cases:
            flight = {
                "departure_airport": "HEL",
                "destination_airport": "BKK",
                "outbound_date": "2024-02-01",
                "return_date": "2024-02-15",
                "price": price_input,
                "airline": "Test Airline",
                "stops": 1,
                "duration": "12h",
                "current_price_indicator": "low",
            }

            # Mock search to return our test flight
            mock_search.return_value = [flight]

            result = await search_flight_combination(
                "HEL",
                "BKK",
                "2024-02-01",
                "2024-02-15",
                {
                    "max_price": 2000.0,
                    "min_duration_days": 13,
                    "max_duration_days": 30,
                    "max_stops": 2,
                },
            )

            assert len(result) == 1
            assert result[0]["price"] == expected_price


@pytest.mark.asyncio(scope="function")
async def test_search_optimization(mock_search, mock_datetime):
    """Test search optimization features."""
    # Mock search to raise an error
    mock_search.side_effect = Exception("Search failed")

    # Mock date range generation
    with patch("api.services.flights.generate_date_range") as mock_date_range:
        mock_date_range.return_value = ["2024-02-01"]

        # Test handling of failed searches
        with pytest.raises(HTTPException) as exc_info:
            await search_flight_combination(
                "XXX",  # Invalid airport
                "YYY",
                "2024-02-01",
                "2024-02-15",
                {
                    "max_price": 1000.0,
                    "min_duration_days": 13,
                    "max_duration_days": 30,
                    "max_stops": 2,
                },
            )
        assert exc_info.value.status_code == 500
        assert "Error searching flights" in str(exc_info.value.detail)


@pytest.mark.asyncio(scope="function")
async def test_progress_tracking():
    """Test progress tracking during search."""
    # Initialize progress tracker
    progress = SearchProgress()

    # Add some tasks
    progress.total_tasks = 10
    task_id = "test-task"
    task_desc = "Test Task"

    # Test tracking
    progress.add_current_search(task_id, task_desc)
    assert len(progress.current_searches) > 0

    progress.increment_found_flights()
    assert progress.found_flights > 0

    progress.update_best_price(450.0)
    assert progress.best_price == 450.0

    progress.increment_completed()
    assert progress.completed_tasks > 0

    progress.remove_current_search(task_id)
    assert task_id not in progress.current_searches
