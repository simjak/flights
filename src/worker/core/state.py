from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import UUID

from ..utils.logger import get_logger

logger = get_logger(__name__)


class JobStatus(str, Enum):
    """Job status enum."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SearchCombination:
    """Search combination details."""

    departure: str
    destination: str
    outbound_date: datetime
    return_date: Optional[datetime] = None
    processed: bool = False
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class JobState:
    """Job state container."""

    job_id: UUID
    status: JobStatus = JobStatus.PENDING
    total_combinations: int = 0
    processed_combinations: int = 0
    failed_combinations: int = 0
    combinations: Dict[str, SearchCombination] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    last_checkpoint: Optional[datetime] = None
    in_progress: Set[str] = field(default_factory=set)

    def add_combination(self, combination: SearchCombination) -> None:
        """Add a search combination to the job."""
        key = self._get_combination_key(combination)
        self.combinations[key] = combination
        self.total_combinations = len(self.combinations)

    def get_combination(self, key: str) -> Optional[SearchCombination]:
        """Get a search combination by key."""
        return self.combinations.get(key)

    def mark_combination_processed(
        self, combination: SearchCombination, error: Optional[str] = None
    ) -> None:
        """Mark a combination as processed."""
        key = self._get_combination_key(combination)
        combination.processed = True
        combination.last_attempt = datetime.utcnow()

        if error:
            combination.error = error
            self.failed_combinations += 1
            self.errors.append(f"{key}: {error}")
        else:
            self.processed_combinations += 1

        self.combinations[key] = combination
        self.in_progress.discard(key)

    def get_next_combination(self) -> Optional[SearchCombination]:
        """Get the next unprocessed combination."""
        for key, combination in self.combinations.items():
            if not combination.processed and key not in self.in_progress:
                self.in_progress.add(key)
                return combination
        return None

    def is_complete(self) -> bool:
        """Check if all combinations have been processed."""
        return (
            self.processed_combinations + self.failed_combinations
            >= self.total_combinations
        )

    def get_progress(self) -> float:
        """Get job progress as a percentage."""
        if self.total_combinations == 0:
            return 0.0
        return (
            (self.processed_combinations + self.failed_combinations)
            / self.total_combinations
            * 100
        )

    @staticmethod
    def _get_combination_key(combination: SearchCombination) -> str:
        """Generate a unique key for a search combination."""
        key_parts = [
            combination.departure,
            combination.destination,
            combination.outbound_date.isoformat(),
        ]
        if combination.return_date:
            key_parts.append(combination.return_date.isoformat())
        return "_".join(key_parts)


class StateManager:
    """Manager for job states."""

    def __init__(self):
        """Initialize state manager."""
        self.states: Dict[UUID, JobState] = {}

    def create_job(self, job_id: UUID) -> JobState:
        """Create a new job state."""
        if job_id in self.states:
            raise ValueError(f"Job {job_id} already exists")

        state = JobState(job_id=job_id)
        self.states[job_id] = state
        return state

    def get_job(self, job_id: UUID) -> Optional[JobState]:
        """Get job state by ID."""
        return self.states.get(job_id)

    def update_job_status(self, job_id: UUID, status: JobStatus) -> None:
        """Update job status."""
        state = self.states.get(job_id)
        if not state:
            raise ValueError(f"Job {job_id} not found")

        state.status = status
        if status == JobStatus.RUNNING and not state.start_time:
            state.start_time = datetime.utcnow()
        elif status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            state.end_time = datetime.utcnow()

    def checkpoint_job(self, job_id: UUID) -> None:
        """Update job checkpoint time."""
        state = self.states.get(job_id)
        if not state:
            raise ValueError(f"Job {job_id} not found")

        state.last_checkpoint = datetime.utcnow()
        logger.debug(f"Job {job_id} checkpointed at {state.last_checkpoint}")

    def cleanup_job(self, job_id: UUID) -> None:
        """Remove job state."""
        if job_id in self.states:
            del self.states[job_id]
            logger.debug(f"Job {job_id} state cleaned up")
