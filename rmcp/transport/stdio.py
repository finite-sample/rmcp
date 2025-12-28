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
from collections.abc import AsyncIterator
from typing import Any

# Windows-specific imports
if sys.platform == "win32":
    import msvcrt
    import os

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

    def __init__(self, max_workers: int = 2):
        super().__init__("stdio")
        self._stdin_reader: asyncio.StreamReader | None = None
        self._stdout_writer: asyncio.StreamWriter | Any = None
        self._shutdown_event = asyncio.Event()
        self._max_workers = max_workers

    async def startup(self) -> None:
        """Initialize stdin/stdout streams."""
        await super().startup()

        # Windows-specific setup
        if sys.platform == "win32":
            logger.info("Configuring Windows-specific event loop and I/O")
            # Switch to SelectorEventLoop on Windows for better pipe handling
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                # Set binary mode for stdin/stdout to prevent line ending issues
                msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
                msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
                logger.info("Windows I/O configuration successful")
            except Exception as e:
                logger.warning(f"Windows I/O configuration failed, continuing: {e}")

        # Set up async stdin/stdout
        loop = asyncio.get_event_loop()

        try:
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
            logger.info("Stdio transport initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize stdio transport: {e}")
            if sys.platform == "win32":
                logger.info("Attempting Windows fallback initialization...")
                await self._windows_fallback_startup()
            else:
                raise

    async def _windows_fallback_startup(self) -> None:
        """Windows-specific fallback initialization using thread-based I/O."""
        import concurrent.futures

        logger.info("Using Windows fallback I/O method")

        # Use ThreadPoolExecutor for blocking I/O operations
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self._max_workers
        )

        # Create a simple stream reader that works with Windows
        self._stdin_reader = asyncio.StreamReader()

        # Create a mock stdout writer for Windows compatibility
        class WindowsStdoutWriter:
            def __init__(self):
                self._buffer = []

            def write(self, data):
                if isinstance(data, str):
                    data = data.encode("utf-8")
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()

            def close(self):
                pass

            async def wait_closed(self):
                pass

        self._stdout_writer = WindowsStdoutWriter()
        logger.info("Windows fallback initialization completed")

    async def _windows_receive_messages(self) -> AsyncIterator[dict[str, Any]]:
        """Windows-specific message reading using thread-based I/O."""
        import asyncio

        def read_stdin_line():
            """Blocking read from stdin in a thread."""
            try:
                return sys.stdin.buffer.readline()
            except Exception as e:
                logger.error(f"Error reading from stdin: {e}")
                return None

        loop = asyncio.get_event_loop()

        while self._running and not self._shutdown_event.is_set():
            try:
                # Read line in thread to avoid blocking
                line_bytes = await loop.run_in_executor(self._executor, read_stdin_line)

                if not line_bytes:
                    logger.info("EOF reached on stdin")
                    break

                try:
                    line_str = line_bytes.decode("utf-8").rstrip("\n\r")
                except UnicodeDecodeError:
                    logger.warning("Failed to decode line, skipping")
                    continue

                if not line_str:
                    continue  # Skip empty lines

                logger.debug(f"Received message: {line_str[:100]}...")

                # Parse JSON-RPC message
                try:
                    message = JSONRPCEnvelope.decode(line_str)
                    # Convert to dict for handler
                    message_dict: dict[str, Any] = {
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
                    continue

            except asyncio.CancelledError:
                logger.info("Windows message reading cancelled")
                break
            except Exception as e:
                logger.error(f"Error in Windows message reading: {e}")
                await asyncio.sleep(0.1)  # Brief pause before retry

    async def shutdown(self) -> None:
        """Clean up streams."""
        await super().shutdown()
        if self._stdout_writer:
            self._stdout_writer.close()
            await self._stdout_writer.wait_closed()

        # Clean up Windows fallback resources
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=True)

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

        # Check if we're using Windows fallback mode
        if sys.platform == "win32" and hasattr(self, "_executor"):
            logger.info("Using Windows fallback message reading")
            async for message in self._windows_receive_messages():
                yield message
            return

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
                        message_dict: dict[str, Any] = {
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
                except TimeoutError:
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
