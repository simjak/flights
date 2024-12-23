import asyncio
import signal
from typing import Set

from sqlalchemy.ext.asyncio import AsyncSession

from ..api.db.service import DatabaseService
from ..api.db.session import get_session
from ..config import get_settings
from .core.flight_search_worker import FlightSearchWorker
from .queue import TaskQueue
from .utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class Worker:
    """Background worker for processing flight search tasks."""

    def __init__(self):
        """Initialize worker."""
        self.running = False
        self.tasks: Set[asyncio.Task] = set()
        self.queue = TaskQueue()
        self.session: AsyncSession | None = None
        self.db: DatabaseService | None = None

    async def start(self) -> None:
        """Start the worker."""
        logger.info("Starting worker...")
        self.running = True

        # Connect to queue
        await self.queue.connect()

        # Get database session
        self.session = await anext(get_session())
        self.db = DatabaseService(self.session)

        # Register signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            asyncio.get_event_loop().add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self.shutdown(s)),
            )

        try:
            # Process tasks
            while self.running:
                try:
                    # Get task from queue
                    message = await self.queue.dequeue()
                    if not message:
                        continue

                    # Process task
                    logger.info(f"Processing task {message.job_id}")
                    job = await self.db.get_job(message.job_id)
                    if not job:
                        logger.error(f"Job {message.job_id} not found")
                        continue

                    # Create worker
                    worker = FlightSearchWorker(self.db)

                    # Start task
                    task = asyncio.create_task(worker.start_job(job))
                    self.tasks.add(task)
                    task.add_done_callback(self.tasks.discard)

                except Exception as e:
                    logger.error(f"Error processing task: {str(e)}", exc_info=True)
                    await asyncio.sleep(1)

        finally:
            await self.cleanup()

    async def shutdown(self, sig: signal.Signals) -> None:
        """
        Shutdown the worker.

        Args:
            sig: Signal that triggered the shutdown
        """
        logger.info(f"Received exit signal {sig.name}...")
        self.running = False

    async def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up...")

        # Cancel running tasks
        for task in self.tasks:
            task.cancel()

        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

        # Close connections
        await self.queue.disconnect()
        if self.session:
            await self.session.close()

        logger.info("Shutdown complete")


async def main() -> None:
    """Run the worker."""
    worker = Worker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
