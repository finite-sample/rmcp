"""
Stdio transport for MCP server.
Implements JSON-RPC 2.0 over stdin/stdout with proper hygiene:
- Never prints to stdout (only stderr for logging)
- One JSON message per line
- Proper error handling and cleanup
- Async I/O for non-blocking operation
Following mature MCP patterns: "stdio servers never print to stdout."
"""

import asyncio
import logging
import sys
from typing import Any, AsyncIterator

from ..transport.base import Transport
from ..transport.jsonrpc import JSONRPCEnvelope, JSONRPCError

# Configure logging to stderr only (never stdout)
logger = logging.getLogger(__name__)


class StdioTransport(Transport):
    """
    Stdio transport using JSON-RPC 2.0 over stdin/stdout.
    Key characteristics:
    - Reads JSON-RPC messages from stdin (one per line)
    - Writes JSON-RPC responses to stdout (one per line)
    - Logs only to stderr (never stdout)
    - Non-blocking async I/O
    - Graceful error handling
    """

    def __init__(self):
        super().__init__("stdio")
        self._stdin_reader: asyncio.StreamReader = None
        self._stdout_writer: asyncio.StreamWriter = None
        self._shutdown_event = asyncio.Event()

    async def startup(self) -> None:
        """Initialize stdin/stdout streams."""
        await super().startup()
        # Set up async stdin/stdout
        loop = asyncio.get_event_loop()
        # Create stdin reader
        self._stdin_reader = asyncio.StreamReader()
        stdin_protocol = asyncio.StreamReaderProtocol(self._stdin_reader)
        await loop.connect_read_pipe(lambda: stdin_protocol, sys.stdin)
        # Create stdout writer
        stdout_transport, stdout_protocol = await loop.connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        self._stdout_writer = asyncio.StreamWriter(
            stdout_transport, stdout_protocol, None, loop
        )
        logger.info("Stdio transport initialized")

    async def shutdown(self) -> None:
        """Clean up streams."""
        await super().shutdown()
        if self._stdout_writer:
            self._stdout_writer.close()
            await self._stdout_writer.wait_closed()
        self._shutdown_event.set()
        logger.info("Stdio transport shutdown complete")

    async def receive_messages(self) -> AsyncIterator[dict[str, Any]]:
        """
        Read JSON-RPC messages from stdin.
        Yields parsed and validated JSON-RPC messages.
        """
        if not self._stdin_reader:
            raise RuntimeError("Transport not started")
        logger.info("Starting to read messages from stdin")
        try:
            while self._running and not self._shutdown_event.is_set():
                try:
                    # Read one line from stdin
                    line = await asyncio.wait_for(
                        self._stdin_reader.readline(),
                        timeout=0.1,  # Short timeout to check shutdown
                    )
                    if not line:
                        # EOF reached
                        logger.info("EOF reached on stdin")
                        break
                    line_str = line.decode("utf-8").rstrip("\n\r")
                    if not line_str:
                        continue  # Skip empty lines
                    logger.debug(f"Received message: {line_str[:100]}...")
                    # Parse JSON-RPC message
                    try:
                        message = JSONRPCEnvelope.decode(line_str)
                        # Convert to dict for handler
                        message_dict = {
                            "jsonrpc": message.jsonrpc,
                            "id": message.id,
                        }
                        if message.method:
                            message_dict["method"] = message.method
                        if message.params is not None:
                            message_dict["params"] = message.params
                        if message.result is not None:
                            message_dict["result"] = message.result
                        if message.error is not None:
                            message_dict["error"] = message.error
                        yield message_dict
                    except JSONRPCError as e:
                        logger.error(f"JSON-RPC parse error: {e}")
                        # Send error response if we can determine request ID
                        error_response = e.to_dict()
                        await self.send_message(error_response)
                except asyncio.TimeoutError:
                    # Timeout is expected, just check if we should continue
                    continue
                except Exception as e:
                    logger.error(f"Error reading from stdin: {e}")
                    break
        except Exception as e:
            logger.error(f"Fatal error in message reception: {e}")
        finally:
            logger.info("Stopped reading messages")

    async def send_message(self, message: dict[str, Any]) -> None:
        """
        Send JSON-RPC message to stdout.
        Encodes message as single line JSON and writes to stdout.
        """
        if not self._stdout_writer:
            raise RuntimeError("Transport not started")
        try:
            # Encode to single-line JSON
            json_line = JSONRPCEnvelope.encode(message)
            logger.debug(f"Sending message: {json_line[:100]}...")
            # Write to stdout with newline
            self._stdout_writer.write((json_line + "\n").encode("utf-8"))
            await self._stdout_writer.drain()
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise

    async def send_notification(self, method: str, params: Any = None) -> None:
        """Send a JSON-RPC notification."""
        notification = JSONRPCEnvelope.create_notification(method, params)
        await self.send_message(notification)

    async def send_progress_notification(
        self, token: str, value: int, total: int, message: str = ""
    ) -> None:
        """Send MCP progress notification."""
        await self.send_notification(
            "notifications/progress",
            {
                "progressToken": token,
                "progress": value,
                "total": total,
                "message": message,
            },
        )

    async def send_log_notification(
        self, level: str, message: str, data: Any = None
    ) -> None:
        """Send MCP log notification."""
        log_params = {"level": level, "message": message}
        if data:
            log_params["data"] = data
        await self.send_notification("notifications/message", log_params)

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        logger.info("Shutdown requested")
        self._shutdown_event.set()
