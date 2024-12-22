from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from api.main import app
from api.models.flights import FlightSearchResponse


@pytest.mark.asyncio(scope="function")
async def test_search_flights_success(mock_flight_data):
    """Test successful flight search."""
    with patch("api.services.flights.search_flights") as mock_search:
        # Configure mock
        mock_search.return_value = mock_flight_data

        # Test data
        request_data = {
            "departure_airports": ["VNO"],
            "destination_airports": ["SIN", "BKK"],
            "start_date": "2025-02-05",
            "end_date": "2025-02-16",
            "min_duration_days": 11,
            "max_duration_days": 30,
            "max_price": 700.0,
            "max_stops": 2,
        }

        # Make request
        with TestClient(app) as client:
            response = client.post("/api/v1/flights/search", json=request_data)

        # Assert response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)

        # Validate response model
        result = FlightSearchResponse(**data)
        assert result.total_results == 2
        assert result.best_price == 650.0
        assert result.search_status == "completed"
        assert len(result.results) == 2


@pytest.mark.asyncio(scope="function")
async def test_search_flights_validation():
    """Test input validation for flight search."""
    # Test invalid dates
    request_data = {
        "departure_airports": ["VNO"],
        "destination_airports": ["SIN"],
        "start_date": "2025-02-16",  # End date before start date
        "end_date": "2025-02-05",
        "min_duration_days": 11,
        "max_duration_days": 30,
    }

    with TestClient(app) as client:
        response = client.post("/api/v1/flights/search", json=request_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert "detail" in data
    assert any("end_date" in error["loc"] for error in data["detail"])

    # Test invalid duration
    request_data = {
        "departure_airports": ["VNO"],
        "destination_airports": ["SIN"],
        "start_date": "2025-02-05",
        "end_date": "2025-02-16",
        "min_duration_days": 30,  # Min greater than max
        "max_duration_days": 11,
    }

    with TestClient(app) as client:
        response = client.post("/api/v1/flights/search", json=request_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert "detail" in data
    assert any("max_duration_days" in error["loc"] for error in data["detail"])


@pytest.mark.asyncio(scope="function")
async def test_search_flights_error_handling():
    """Test error handling in flight search."""
    with patch("api.services.flights.search_flights") as mock_search:
        # Configure mock to raise an exception
        mock_search.side_effect = Exception("Search failed")

        # Test data
        request_data = {
            "departure_airports": ["VNO"],
            "destination_airports": ["SIN"],
            "start_date": "2025-02-05",
            "end_date": "2025-02-16",
            "min_duration_days": 11,
            "max_duration_days": 30,
        }

        # Make request
        with TestClient(app) as client:
            response = client.post("/api/v1/flights/search", json=request_data)

        # Assert response
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "error" in data["detail"].lower()
