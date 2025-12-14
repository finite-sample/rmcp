"""Type definitions for JSON-RPC, MCP protocol, and configuration structures."""

from typing import Any, Literal, NotRequired, TypedDict

# JSON-RPC 2.0 Types
JSONRPCVersion = Literal["2.0"]
JSONRPCId = str | int | None


class JSONRPCRequest(TypedDict):
    """JSON-RPC 2.0 request message."""

    jsonrpc: JSONRPCVersion
    method: str
    params: NotRequired[dict[str, Any] | list[Any]]
    id: NotRequired[JSONRPCId]


class JSONRPCResponse(TypedDict):
    """JSON-RPC 2.0 successful response message."""

    jsonrpc: JSONRPCVersion
    result: Any
    id: JSONRPCId


class JSONRPCError(TypedDict):
    """JSON-RPC 2.0 error object."""

    code: int
    message: str
    data: NotRequired[Any]


class JSONRPCErrorResponse(TypedDict):
    """JSON-RPC 2.0 error response message."""

    jsonrpc: JSONRPCVersion
    error: JSONRPCError
    id: JSONRPCId


# MCP Protocol Types
MCPProtocolVersion = Literal["2025-11-25", "2025-06-18"]


class MCPClientInfo(TypedDict):
    """MCP client information."""

    name: str
    version: str


class MCPServerInfo(TypedDict):
    """MCP server information."""

    name: str
    version: str


class MCPCapabilities(TypedDict):
    """MCP server capabilities."""

    tools: NotRequired[dict[str, Any]]
    resources: NotRequired[dict[str, Any]]
    prompts: NotRequired[dict[str, Any]]
    logging: NotRequired[dict[str, Any]]
    completion: NotRequired[dict[str, Any]]


class MCPInitializeParams(TypedDict):
    """MCP initialize request parameters."""

    protocolVersion: MCPProtocolVersion
    capabilities: MCPCapabilities
    clientInfo: MCPClientInfo


class MCPInitializeResult(TypedDict):
    """MCP initialize response result."""

    protocolVersion: MCPProtocolVersion
    capabilities: MCPCapabilities
    serverInfo: MCPServerInfo
    instructions: NotRequired[str]


# Tool Execution Types
class MCPToolCall(TypedDict):
    """MCP tool call parameters."""

    name: str
    arguments: NotRequired[dict[str, Any]]


class MCPToolResult(TypedDict):
    """MCP tool execution result."""

    content: list[dict[str, Any]]
    isError: NotRequired[bool]


# Configuration Types
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
TransportType = Literal["stdio", "http", "https"]
OutputFormat = Literal["json", "table", "yaml", "pretty"]
AnalysisType = Literal[
    "regression", "correlation", "anova", "classification", "general"
]

# HTTP Transport Types
CORSOrigin = str | Literal["*"]


class HTTPConfig(TypedDict):
    """HTTP transport configuration."""

    host: str
    port: int
    cors_origins: list[CORSOrigin]
    ssl_keyfile: NotRequired[str | None]
    ssl_certfile: NotRequired[str | None]
    ssl_keyfile_password: NotRequired[str | None]


class LoggingConfig(TypedDict):
    """Logging configuration."""

    level: LogLevel
    format: NotRequired[str]
    file: NotRequired[str | None]


class SecurityConfig(TypedDict):
    """Security configuration."""

    vfs_allowed_paths: list[str]
    vfs_read_only: bool


class RConfig(TypedDict):
    """R integration configuration."""

    timeout: int
    max_sessions: int
    binary_path: NotRequired[str | None]


class RMCPConfig(TypedDict):
    """Complete RMCP configuration."""

    debug: bool
    http: HTTPConfig
    logging: LoggingConfig
    security: SecurityConfig
    r: RConfig
    config_file: NotRequired[str | None]


# R Execution Types
RPackageStatus = Literal["installed", "missing", "outdated"]
RExecutionStatus = Literal["success", "error", "timeout"]


class RPackageInfo(TypedDict):
    """R package information."""

    name: str
    version: NotRequired[str]
    status: RPackageStatus
    required_version: NotRequired[str]


class RExecutionResult(TypedDict):
    """R script execution result."""

    status: RExecutionStatus
    result: NotRequired[dict[str, Any]]
    stdout: NotRequired[str]
    stderr: NotRequired[str]
    execution_time_ms: int
    packages_used: NotRequired[list[str]]
    error_message: NotRequired[str]


# Statistical Analysis Types
StatisticalMethod = Literal[
    "linear_regression",
    "logistic_regression",
    "anova",
    "t_test",
    "correlation",
    "chi_square",
    "arima",
    "clustering",
    "decision_tree",
]


class StatisticalResult(TypedDict):
    """Statistical analysis result."""

    method: StatisticalMethod
    summary: dict[str, Any]
    statistics: dict[str, float]
    p_values: NotRequired[dict[str, float]]
    confidence_intervals: NotRequired[dict[str, tuple[float, float]]]
    diagnostics: NotRequired[dict[str, Any]]
    interpretation: NotRequired[str]


# Security and Approval Types
SecurityLevel = Literal["low", "medium", "high", "critical"]
ApprovalStatus = Literal["pending", "approved", "denied"]
OperationType = Literal["file_operations", "package_installation", "system_operations"]


class SecurityEvent(TypedDict):
    """Security event information."""

    event_type: str
    operation: str
    security_level: SecurityLevel
    approved: bool
    timestamp: str
    session_id: NotRequired[str]
    details: NotRequired[dict[str, Any]]


class OperationApproval(TypedDict):
    """Operation approval request."""

    operation_type: OperationType
    operation_name: str
    description: str
    security_level: SecurityLevel
    status: ApprovalStatus
    session_only: bool


# Export all types
__all__ = [
    # JSON-RPC types
    "JSONRPCVersion",
    "JSONRPCId",
    "JSONRPCRequest",
    "JSONRPCResponse",
    "JSONRPCError",
    "JSONRPCErrorResponse",
    # MCP types
    "MCPProtocolVersion",
    "MCPClientInfo",
    "MCPServerInfo",
    "MCPCapabilities",
    "MCPInitializeParams",
    "MCPInitializeResult",
    "MCPToolCall",
    "MCPToolResult",
    # Configuration types
    "LogLevel",
    "TransportType",
    "OutputFormat",
    "AnalysisType",
    "CORSOrigin",
    "HTTPConfig",
    "LoggingConfig",
    "SecurityConfig",
    "RConfig",
    "RMCPConfig",
    # R execution types
    "RPackageStatus",
    "RExecutionStatus",
    "RPackageInfo",
    "RExecutionResult",
    # Statistical types
    "StatisticalMethod",
    "StatisticalResult",
    # Security types
    "SecurityLevel",
    "ApprovalStatus",
    "OperationType",
    "SecurityEvent",
    "OperationApproval",
]
