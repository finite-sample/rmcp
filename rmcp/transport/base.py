"""
Base transport interface for MCP server.
Defines the contract that all transports must implement,
enabling clean composition at the server edge.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


class Transport(ABC):
    """
    Abstract base class for MCP transports.
    All transports must implement:
    - Message receiving (async iterator)
    - Message sending
    - Lifecycle management (startup/shutdown)
    - Error handling
    """

    def __init__(self, name: str):
        self.name = name
        self._running = False
        self._message_handler: (
            Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]] | None
        ) = None

    def set_message_handler(
        self, handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]]
    ) -> None:
        """Set the message handler that will process incoming messages."""
        self._message_handler = handler

    @abstractmethod
    async def startup(self) -> None:
        """Initialize the transport."""
        logger.info(f"Starting {self.name} transport")
        self._running = True

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up the transport."""
        logger.info(f"Shutting down {self.name} transport")
        self._running = False

    @abstractmethod
    def receive_messages(self) -> AsyncIterator[dict[str, Any]]:
        """
        Async iterator that yields incoming messages.
        Messages are already parsed from transport format (JSON-RPC).
        """
        pass

    @abstractmethod
    async def send_message(self, message: dict[str, Any]) -> None:
        """
        Send a message via the transport.
        Message will be encoded to transport format (JSON-RPC).
        """
        pass

    async def run(self) -> None:
        """
        Run the transport event loop.
        This is the main entry point that:
        1. Starts the transport
        2. Processes incoming messages
        3. Handles errors gracefully
        4. Ensures clean shutdown
        """
        if not self._message_handler:
            raise RuntimeError("Message handler not set")
        try:
            await self.startup()
            async for message in self.receive_messages():
                try:
                    # Process message through handler
                    response = await self._message_handler(message)
                    # Send response if there is one
                    if response:
                        await self.send_message(response)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Send error response if possible
                    error_response = self._create_error_response(message, e)
                    if error_response:
                        try:
                            await self.send_message(error_response)
                        except Exception as send_error:
                            logger.error(f"Failed to send error response: {send_error}")
        except Exception as e:
            logger.error(f"Transport error: {e}")
        finally:
            await self.shutdown()

    def _create_error_response(
        self, request: dict[str, Any], error: Exception
    ) -> dict[str, Any] | None:
        """Create an error response for a failed request."""
        request_id = request.get("id")
        if request_id is None:
            # No ID means no response expected (notification)
            return None
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,  # Internal error
                "message": str(error),
                "data": {"type": type(error).__name__},
            },
        }

    @property
    def is_running(self) -> bool:
        """Check if transport is running."""
        return self._running
