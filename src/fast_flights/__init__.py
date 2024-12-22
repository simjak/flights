"""Fast Flights - A Python library for searching flights."""

from .core import get_flights
from .flights_impl import FlightData, TFSData, create_filter
from .schema import Flight, Result
from .search import search_flights
from .types import Passengers

__all__ = [
    "get_flights",
    "FlightData",
    "TFSData",
    "create_filter",
    "Flight",
    "Passengers",
    "Result",
    "search_flights",
]
