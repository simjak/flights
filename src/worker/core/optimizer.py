from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SearchPattern:
    """Search pattern with success/failure tracking."""

    departure: str
    destination: str
    success_count: int = 0
    failure_count: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    avg_price: Optional[float] = None
    total_flights: int = 0


@dataclass
class SearchOptimizer:
    """Optimizes search patterns based on historical data."""

    max_concurrent_searches: int
    patterns: Dict[str, SearchPattern] = field(default_factory=dict)
    failed_patterns: Set[str] = field(default_factory=set)
    successful_patterns: Dict[str, int] = field(default_factory=dict)
    _cache: Dict[str, List[dict]] = field(default_factory=dict)

    def get_pattern_key(self, departure: str, destination: str) -> str:
        """Generate a unique key for a search pattern."""
        return f"{departure}-{destination}"

    def record_success(
        self,
        departure: str,
        destination: str,
        price: Optional[float] = None,
        results: Optional[List[dict]] = None,
    ) -> None:
        """Record a successful search pattern."""
        key = self.get_pattern_key(departure, destination)
        pattern = self.patterns.get(key)

        if not pattern:
            pattern = SearchPattern(departure=departure, destination=destination)
            self.patterns[key] = pattern

        pattern.success_count += 1
        pattern.last_success = datetime.utcnow()

        if results:
            pattern.total_flights += len(results)
            if price:
                # Update average price
                if pattern.avg_price is None:
                    pattern.avg_price = price
                else:
                    pattern.avg_price = (pattern.avg_price + price) / 2

        # Cache results for potential reuse
        if results:
            self._cache[key] = results

        # Update successful patterns count
        self.successful_patterns[key] = pattern.success_count

        # Remove from failed patterns if present
        self.failed_patterns.discard(key)

        logger.debug(
            f"Recorded success for {key}: "
            f"success_count={pattern.success_count}, "
            f"avg_price={pattern.avg_price}"
        )

    def record_failure(self, departure: str, destination: str) -> None:
        """Record a failed search pattern."""
        key = self.get_pattern_key(departure, destination)
        pattern = self.patterns.get(key)

        if not pattern:
            pattern = SearchPattern(departure=departure, destination=destination)
            self.patterns[key] = pattern

        pattern.failure_count += 1
        pattern.last_failure = datetime.utcnow()

        # Add to failed patterns if failure rate is high
        if pattern.failure_count > pattern.success_count:
            self.failed_patterns.add(key)

        logger.debug(
            f"Recorded failure for {key}: " f"failure_count={pattern.failure_count}"
        )

    def optimize_search_order(
        self,
        combinations: List[Tuple[str, str, str, str]],
    ) -> List[Tuple[str, str, str, str]]:
        """
        Optimize the order of search combinations based on historical data.

        Args:
            combinations: List of (departure, destination, outbound_date, return_date)
        """

        def get_pattern_score(combo: Tuple[str, str, str, str]) -> float:
            departure, destination, _, _ = combo
            key = self.get_pattern_key(departure, destination)
            pattern = self.patterns.get(key)

            if not pattern:
                return 0.0

            if key in self.failed_patterns:
                return -1.0

            # Calculate score based on success rate and recency
            total_attempts = pattern.success_count + pattern.failure_count
            if total_attempts == 0:
                success_rate = 0.0
            else:
                success_rate = pattern.success_count / total_attempts

            # Bonus for recent successes
            recency_bonus = 0.0
            if pattern.last_success:
                time_since_success = (
                    datetime.utcnow() - pattern.last_success
                ).total_seconds()
                recency_bonus = 1.0 / (
                    1.0 + time_since_success / 3600
                )  # Decay over hours

            return success_rate + recency_bonus

        # Sort combinations by score
        scored_combinations = [
            (combo, get_pattern_score(combo)) for combo in combinations
        ]
        scored_combinations.sort(key=lambda x: x[1], reverse=True)

        optimized = [combo for combo, _ in scored_combinations]

        logger.debug(
            f"Optimized {len(combinations)} combinations. "
            f"Top pattern score: {scored_combinations[0][1] if scored_combinations else 0.0}"
        )

        return optimized

    def get_cached_results(
        self,
        departure: str,
        destination: str,
    ) -> Optional[List[dict]]:
        """Get cached results for a pattern if available."""
        key = self.get_pattern_key(departure, destination)
        return self._cache.get(key)

    def clear_cache(self) -> None:
        """Clear the results cache."""
        self._cache.clear()

    def get_pattern_stats(self) -> Dict[str, dict]:
        """Get statistics for all patterns."""
        return {
            key: {
                "success_count": pattern.success_count,
                "failure_count": pattern.failure_count,
                "avg_price": pattern.avg_price,
                "total_flights": pattern.total_flights,
                "last_success": pattern.last_success,
                "last_failure": pattern.last_failure,
            }
            for key, pattern in self.patterns.items()
        }
