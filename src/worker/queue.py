import json
from typing import Any, Dict, Optional
from uuid import UUID

import aio_pika
from pydantic import BaseModel

from config import get_settings

settings = get_settings()


class TaskMessage(BaseModel):
    """Task message for the queue."""

    job_id: UUID
    task_type: str
    payload: Dict[str, Any]

    def model_dump(self, **kwargs):
        """Override model_dump to handle UUID serialization."""
        data = super().model_dump(**kwargs)
        data["job_id"] = str(data["job_id"])
        return data


class TaskQueue:
    """Task queue using RabbitMQ."""

    def __init__(self):
        """Initialize task queue."""
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.queue_name = "flight_search_tasks"
        self.exchange_name = "flight_search"

    async def connect(self) -> None:
        """Connect to RabbitMQ."""
        if not self.connection:
            if not settings.RABBITMQ_URL:
                raise ValueError("RABBITMQ_URL is required")

            # Connect to RabbitMQ
            self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            self.channel = await self.connection.channel()

            # Declare exchange and queue
            exchange = await self.channel.declare_exchange(
                self.exchange_name,
                aio_pika.ExchangeType.DIRECT,
                durable=True,
            )

            queue = await self.channel.declare_queue(
                self.queue_name,
                durable=True,
                auto_delete=False,
            )

            # Bind queue to exchange
            await queue.bind(exchange, routing_key=self.queue_name)

    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ."""
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.channel = None

    async def enqueue(self, message: TaskMessage) -> None:
        """
        Add a task to the queue.

        Args:
            message: Task message
        """
        if not self.channel:
            await self.connect()

        # Create message
        message_body = json.dumps(message.model_dump()).encode()
        message = aio_pika.Message(
            message_body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        # Get exchange
        exchange = await self.channel.get_exchange(self.exchange_name)

        # Publish message
        await exchange.publish(
            message,
            routing_key=self.queue_name,
        )

    async def dequeue(self) -> Optional[TaskMessage]:
        """
        Get a task from the queue.

        Returns:
            Task message if available, None otherwise
        """
        if not self.channel:
            await self.connect()

        # Get queue
        queue = await self.channel.get_queue(self.queue_name)

        # Get message
        message = await queue.get(timeout=1)
        if not message:
            return None

        try:
            # Parse message
            message_data = json.loads(message.body.decode())
            task = TaskMessage(**message_data)

            # Acknowledge message
            await message.ack()

            return task
        except Exception as e:
            # Reject message on error
            await message.reject(requeue=True)
            raise e

    async def __aenter__(self) -> "TaskQueue":
        """Enter async context."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context."""
        await self.disconnect()
