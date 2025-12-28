"""Exception classes for R execution and MCP protocol errors."""

from collections.abc import Sequence
from typing import Any


class RMCPError(Exception):
    """Base exception for all RMCP-related errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}


class RExecutionError(RMCPError):
    """R script execution error with detailed context."""

    def __init__(
        self,
        message: str,
        stdout: str = "",
        stderr: str = "",
        returncode: int | None = None,
        execution_time_ms: int | None = None,
        r_command: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, context)
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.execution_time_ms = execution_time_ms
        self.r_command = r_command


class RPackageError(RMCPError):
    """R package-related error."""

    def __init__(
        self,
        message: str,
        package_name: str | None = None,
        required_version: str | None = None,
        installed_version: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, context)
        self.package_name = package_name
        self.required_version = required_version
        self.installed_version = installed_version


class ConfigurationError(RMCPError):
    """Configuration validation or loading error."""

    def __init__(
        self,
        message: str,
        config_path: str | None = None,
        invalid_keys: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, context)
        self.config_path = config_path
        self.invalid_keys = invalid_keys or []


class ValidationError(RMCPError):
    """Data or schema validation error."""

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        expected_type: str | None = None,
        actual_value: Any = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, context)
        self.field_name = field_name
        self.expected_type = expected_type
        self.actual_value = actual_value


class SecurityError(RMCPError):
    """Security-related error (approval denied, access forbidden, etc.)."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        security_level: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, context)
        self.operation = operation
        self.security_level = security_level


class RExecutionErrorGroup(ExceptionGroup):
    """Group of R execution errors using Python 3.11+ ExceptionGroup."""

    def __init__(self, message: str, exceptions: Sequence[Exception]):
        super().__init__(message, exceptions)

    @classmethod
    def from_multiple_failures(
        cls,
        errors: list[RExecutionError],
        context: str = "Multiple R execution failures",
    ) -> "RExecutionErrorGroup":
        """Create an error group from multiple R execution errors."""
        return cls(context, errors)

    @classmethod
    def from_package_failures(
        cls,
        package_errors: list[RPackageError],
        context: str = "Multiple R package errors",
    ) -> "RExecutionErrorGroup":
        """Create an error group from multiple package errors."""
        return cls(context, package_errors)

    def get_package_errors(self) -> list[RPackageError]:
        """Get all package-related errors from the group."""
        return [e for e in self.exceptions if isinstance(e, RPackageError)]

    def get_execution_errors(self) -> list[RExecutionError]:
        """Get all execution-related errors from the group."""
        return [e for e in self.exceptions if isinstance(e, RExecutionError)]

    def get_error_summary(self) -> dict[str, Any]:
        """Get a structured summary of all errors in the group."""
        summary = {
            "total_errors": len(self.exceptions),
            "error_types": {},
            "packages_affected": set(),
            "common_issues": [],
        }

        for exc in self.exceptions:
            error_type = type(exc).__name__
            summary["error_types"][error_type] = (
                summary["error_types"].get(error_type, 0) + 1
            )

            if isinstance(exc, RPackageError) and exc.package_name:
                summary["packages_affected"].add(exc.package_name)

        summary["packages_affected"] = list(summary["packages_affected"])
        return summary


def handle_r_package_validation(packages: list[str]) -> None:
    """
    Validate R packages and raise ExceptionGroup for multiple failures.

    This function demonstrates modern exception handling by collecting
    all package validation errors and raising them as a group.
    """
    errors: list[RPackageError] = []

    # This would be integrated with actual R package checking
    for package in packages:
        try:
            # Placeholder for actual package validation
            if package.startswith("invalid_"):
                raise RPackageError(
                    f"Package '{package}' is not available",
                    package_name=package,
                    context={"validation_method": "check_availability"},
                )
        except RPackageError as e:
            errors.append(e)

    if errors:
        raise RExecutionErrorGroup.from_package_failures(
            errors, f"Failed to validate {len(errors)} R packages"
        )


def handle_r_script_execution(scripts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Execute multiple R scripts and handle errors with ExceptionGroup.

    Returns successful results and raises ExceptionGroup for failures.
    """
    results = []
    errors: list[RExecutionError] = []

    for i, script_info in enumerate(scripts):
        try:
            # Placeholder for actual R script execution
            script_content = script_info.get("content", "")
            if "error" in script_content.lower():
                raise RExecutionError(
                    f"Script {i} failed execution",
                    stderr=f"Error in script: {script_content[:50]}...",
                    returncode=1,
                    execution_time_ms=100,
                    r_command=script_content[:100],
                    context={"script_index": i, "script_id": script_info.get("id")},
                )

            # Successful execution
            results.append(
                {
                    "script_index": i,
                    "result": {
                        "success": True,
                        "output": "Script executed successfully",
                    },
                }
            )

        except RExecutionError as e:
            errors.append(e)

    # If there were errors, raise them as a group
    if errors:
        raise RExecutionErrorGroup.from_multiple_failures(
            errors, f"Failed to execute {len(errors)} out of {len(scripts)} R scripts"
        )

    return results


__all__ = [
    "RMCPError",
    "RExecutionError",
    "RPackageError",
    "ConfigurationError",
    "ValidationError",
    "SecurityError",
    "RExecutionErrorGroup",
    "handle_r_package_validation",
    "handle_r_script_execution",
]
