from typing import Generator

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_flight_data():
    """Mock flight search results."""
    return [
        {
            "departure_airport": "VNO",
            "destination_airport": "SIN",
            "outbound_date": "2025-02-05",
            "return_date": "2025-02-16",
            "price": 650.0,
            "airline": "Turkish Airlines",
            "stops": 1,
            "duration": "14h 30m",
            "current_price_indicator": "low",
        },
        {
            "departure_airport": "VNO",
            "destination_airport": "BKK",
            "outbound_date": "2025-02-06",
            "return_date": "2025-02-17",
            "price": 700.0,
            "airline": "Emirates",
            "stops": 2,
            "duration": "16h 45m",
            "current_price_indicator": "typical",
        },
    ]
