"""Test script for Flight Search API."""

import asyncio
import json
from datetime import datetime, timedelta

import httpx
import pandas as pd
from IPython.display import HTML, display

# API configuration
API_URL = "http://localhost:8000/api/v1"

# Default search parameters
departure_airports = ["VNO", "RIX", "WAW"]
destination_airports = ["SIN", "BKK", "KUL"]

# Calculate dates
start_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
end_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")


def format_price(price: float) -> str:
    """Format price with currency symbol."""
    return f"€{price:,.2f}"


def create_search_request(
    *,
    departure_airports: list[str],
    destination_airports: list[str],
    start_date: str,
    end_date: str,
    min_duration_days: int = 13,
    max_duration_days: int = 30,
    max_price: float = 700.0,
    max_stops: int = 2,
    max_concurrent_searches: int = 3,
) -> dict:
    """Create a search request payload."""
    return {
        "departure_airports": departure_airports,
        "destination_airports": destination_airports,
        "start_date": start_date,
        "end_date": end_date,
        "min_duration_days": min_duration_days,
        "max_duration_days": max_duration_days,
        "max_price": max_price,
        "max_stops": max_stops,
        "max_concurrent_searches": max_concurrent_searches,
    }


def display_results(response_data: dict) -> None:
    """Display search results in a formatted table."""
    if not response_data.get("results"):
        print("No flights found matching your criteria.")
        return

    # Create DataFrame
    df = pd.DataFrame(response_data["results"])

    # Format columns
    df["price"] = df["price"].apply(format_price)
    df["route"] = df["departure_airport"] + " → " + df["destination_airport"]
    df["dates"] = df["outbound_date"] + " - " + df["return_date"]

    # Select and reorder columns
    display_columns = [
        "route",
        "dates",
        "price",
        "airline",
        "stops",
        "duration",
        "current_price_indicator",
    ]

    # Display summary
    print(f"Found {response_data['total_results']} flights")
    if response_data.get("best_price"):
        print(f"Best price: {format_price(response_data['best_price'])}")
    print(f"Search status: {response_data['search_status']}\n")

    # Display table
    display(HTML(df[display_columns].to_html(index=False)))


async def test_basic_search():
    """Test basic flight search."""
    # Create search request
    request_data = create_search_request(
        departure_airports=departure_airports,
        destination_airports=destination_airports,
        start_date=start_date,
        end_date=end_date,
        max_price=700.0,
    )

    # Make request
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_URL}/flights/search", json=request_data)

    # Display results
    if response.status_code == 200:
        display_results(response.json())
    else:
        print(f"Error: {response.status_code}")
        print(response.json())


async def test_error_handling():
    """Test error handling."""
    # Test invalid dates
    invalid_request = create_search_request(
        departure_airports=departure_airports,
        destination_airports=destination_airports,
        start_date=end_date,  # Swapped dates
        end_date=start_date,
        max_price=700.0,
    )

    # Make request
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_URL}/flights/search", json=invalid_request)

    print(f"Status code: {response.status_code}")
    print("Error details:")
    print(json.dumps(response.json(), indent=2))


async def test_custom_parameters():
    """Test with different parameters."""
    # Test with different parameters
    custom_request = create_search_request(
        departure_airports=["VNO"],
        destination_airports=["SIN"],
        start_date=start_date,
        end_date=end_date,
        min_duration_days=15,
        max_duration_days=20,
        max_price=800.0,
        max_stops=1,
    )

    # Make request
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_URL}/flights/search", json=custom_request)

    # Display results
    if response.status_code == 200:
        display_results(response.json())
    else:
        print(f"Error: {response.status_code}")
        print(response.json())


async def main():
    """Run all tests."""
    print("Testing basic search...")
    await test_basic_search()

    print("\nTesting error handling...")
    await test_error_handling()

    print("\nTesting custom parameters...")
    await test_custom_parameters()


if __name__ == "__main__":
    asyncio.run(main())
