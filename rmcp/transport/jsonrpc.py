"""
JSON-RPC 2.0 envelope handling.
Implements proper JSON-RPC 2.0 specification:
- Request/response/notification parsing
- Error code handling per spec
- Message validation
- Single-line encoding for stdio transport
Following the principle: "No hand-rolled JSON-RPC, no 'close enough' message shapes."
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class JSONRPCError(Exception):
    """JSON-RPC error with proper error code."""

    # Standard JSON-RPC 2.0 error codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    def __init__(
        self, code: int, message: str, data: Any = None, request_id: Any = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data
        self.request_id = request_id

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-RPC error response format."""
        error_obj = {"code": self.code, "message": self.message}
        if self.data is not None:
            error_obj["data"] = self.data
        response = {"jsonrpc": "2.0", "id": self.request_id, "error": error_obj}
        return response


@dataclass
class JSONRPCMessage:
    """Parsed JSON-RPC message."""

    jsonrpc: str
    id: str | int | None | None = None
    method: str | None = None
    params: dict[str, Any] | list | None = None
    result: Any | None = None
    error: dict[str, Any] | None = None

    @property
    def is_request(self) -> bool:
        """Check if this is a request message."""
        return self.method is not None and self.id is not None

    @property
    def is_notification(self) -> bool:
        """Check if this is a notification message."""
        return self.method is not None and self.id is None

    @property
    def is_response(self) -> bool:
        """Check if this is a response message."""
        return self.method is None and (
            self.result is not None or self.error is not None
        )


class JSONRPCEnvelope:
    """JSON-RPC 2.0 message envelope handler."""

    @staticmethod
    def encode(message: dict[str, Any]) -> str:
        """
        Encode message to single-line JSON for stdio transport.
        Following the principle: "One JSON-RPC message per line."
        """
        try:
            # Ensure no embedded newlines in the JSON
            json_str = json.dumps(message, separators=(",", ":"), ensure_ascii=False)
            # Validate it's actually single line
            if "\n" in json_str or "\r" in json_str:
                # This should not happen with separators, but be safe
                json_str = json_str.replace("\n", "\\n").replace("\r", "\\r")
            return json_str
        except (TypeError, ValueError) as e:
            raise JSONRPCError(
                JSONRPCError.INTERNAL_ERROR,
                f"Failed to encode JSON-RPC message: {e}",
                data={"original_message": str(message)[:200]},  # Truncate for safety
            )

    @staticmethod
    def decode(line: str) -> JSONRPCMessage:
        """
        Decode single line of JSON to JSON-RPC message.
        Validates JSON-RPC 2.0 specification compliance.
        """
        if not line.strip():
            raise JSONRPCError(JSONRPCError.INVALID_REQUEST, "Empty message")
        try:
            data = json.loads(line.strip())
        except json.JSONDecodeError as e:
            raise JSONRPCError(JSONRPCError.PARSE_ERROR, f"Invalid JSON: {e}") from e
        # Validate JSON-RPC 2.0 structure
        if not isinstance(data, dict):
            raise JSONRPCError(
                JSONRPCError.INVALID_REQUEST, "JSON-RPC message must be an object"
            )
        jsonrpc_version = data.get("jsonrpc")
        if jsonrpc_version != "2.0":
            raise JSONRPCError(
                JSONRPCError.INVALID_REQUEST,
                f"Invalid JSON-RPC version: {jsonrpc_version}. Must be '2.0'",
            )
        # Extract message components
        message = JSONRPCMessage(
            jsonrpc=jsonrpc_version,
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error"),
        )
        # Validate message type
        if message.is_request or message.is_notification:
            if not isinstance(message.method, str):
                raise JSONRPCError(
                    JSONRPCError.INVALID_REQUEST,
                    "Method must be a string",
                    request_id=message.id,
                )
            # Params are optional, but if present must be object or array
            if message.params is not None:
                if not isinstance(message.params, dict | list):
                    raise JSONRPCError(
                        JSONRPCError.INVALID_REQUEST,
                        "Params must be object or array",
                        request_id=message.id,
                    )
        elif message.is_response:
            # Response must have either result or error, not both
            has_result = message.result is not None
            has_error = message.error is not None
            if has_result and has_error:
                raise JSONRPCError(
                    JSONRPCError.INVALID_REQUEST,
                    "Response cannot have both result and error",
                    request_id=message.id,
                )
            if not has_result and not has_error:
                raise JSONRPCError(
                    JSONRPCError.INVALID_REQUEST,
                    "Response must have either result or error",
                    request_id=message.id,
                )
        else:
            raise JSONRPCError(
                JSONRPCError.INVALID_REQUEST,
                "Invalid message type",
                request_id=data.get("id"),
            )
        return message

    @staticmethod
    def create_request(
        method: str,
        params: dict[str, Any] | list | None = None,
        request_id: str | int = "1",
    ) -> dict[str, Any]:
        """Create a JSON-RPC 2.0 request."""
        request: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "id": request_id}
        if params is not None:
            request["params"] = params
        return request

    @staticmethod
    def create_notification(
        method: str, params: dict[str, Any] | list | None = None
    ) -> dict[str, Any]:
        """Create a JSON-RPC 2.0 notification."""
        notification: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            notification["params"] = params
        return notification

    @staticmethod
    def create_response(request_id: str | int, result: Any) -> dict[str, Any]:
        """Create a JSON-RPC 2.0 success response."""
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def create_error_response(
        request_id: str | int | None, error: JSONRPCError
    ) -> dict[str, Any]:
        """Create a JSON-RPC 2.0 error response."""
        return error.to_dict()
