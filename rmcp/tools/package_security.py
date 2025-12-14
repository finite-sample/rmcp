"""
R Package Security and Risk Assessment for RMCP.

This module provides security assessment and filtering capabilities for R packages,
including risk categorization and filtering based on security criteria.
"""

from enum import Enum

from ..logging_config import configure_structured_logging, get_logger

logger = get_logger(__name__)


class SecurityLevel(Enum):
    """Security risk levels for R packages."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PackageRiskCategory(Enum):
    """Categories of package security risks."""

    SYSTEM_ACCESS = "system_access"
    NETWORK_ACCESS = "network_access"
    FILE_OPERATIONS = "file_operations"
    CODE_EXECUTION = "code_execution"
    CRYPTO_SECURITY = "crypto_security"
    EXTERNAL_DEPENDENCIES = "external_dependencies"


# Packages that typically involve system-level operations
SYSTEM_ACCESS_PACKAGES = {
    "R.utils",
    "RAppArmor",
    "unix",
    "processx",
    "callr",
    "sys",
    "RCurl",
    "curl",
    "httr",
    "httr2",
    "rvest",
    "downloader",
    "pingr",
    "urltools",
    "webutils",
    "servr",
}

# Packages that involve network operations
NETWORK_ACCESS_PACKAGES = {
    "RCurl",
    "curl",
    "httr",
    "httr2",
    "rvest",
    "xml2",
    "jsonlite",
    "pingr",
    "downloader",
    "googledrive",
    "googlesheets4",
    "gh",
    "pins",
    "plumber",
    "httpuv",
    "websocket",
    "webutils",
}

# Packages that may involve direct file system operations
FILE_OPERATION_PACKAGES = {
    "R.utils",
    "tools",
    "readr",
    "readxl",
    "writexl",
    "openxlsx",
    "haven",
    "foreign",
    "rio",
    "data.table",
    "fst",
    "feather",
    "archive",
    "zip",
    "tar",
    "R.cache",
}

# Packages involving code execution or compilation
CODE_EXECUTION_PACKAGES = {
    "Rcpp",
    "RcppArmadillo",
    "inline",
    "compiler",
    "devtools",
    "remotes",
    "pak",
    "rstan",
    "rstanarm",
    "tensorflow",
    "torch",
    "reticulate",
    "JuliaCall",
    "RJulia",
    "V8",
    "rJava",
}

# Packages with external system dependencies
EXTERNAL_DEPENDENCY_PACKAGES = {
    "rJava",
    "RMySQL",
    "RPostgreSQL",
    "ROracle",
    "RODBC",
    "odbc",
    "Cairo",
    "tkrplot",
    "tcltk",
    "Rgtk2",
    "cairoDevice",
    "rgl",
    "rgdal",
    "rgeos",
    "sf",
    "terra",
    "gdalUtils",
}


def assess_package_security_risk(
    package_name: str,
) -> tuple[SecurityLevel, list[PackageRiskCategory]]:
    """
    Assess the security risk level and categories for an R package.

    Args:
        package_name: Name of the R package

    Returns:
        Tuple of (SecurityLevel, List of risk categories)
    """
    risks = []

    if package_name in SYSTEM_ACCESS_PACKAGES:
        risks.append(PackageRiskCategory.SYSTEM_ACCESS)

    if package_name in NETWORK_ACCESS_PACKAGES:
        risks.append(PackageRiskCategory.NETWORK_ACCESS)

    if package_name in FILE_OPERATION_PACKAGES:
        risks.append(PackageRiskCategory.FILE_OPERATIONS)

    if package_name in CODE_EXECUTION_PACKAGES:
        risks.append(PackageRiskCategory.CODE_EXECUTION)

    if package_name in EXTERNAL_DEPENDENCY_PACKAGES:
        risks.append(PackageRiskCategory.EXTERNAL_DEPENDENCIES)

    # Determine overall security level
    if (
        PackageRiskCategory.SYSTEM_ACCESS in risks
        or PackageRiskCategory.CODE_EXECUTION in risks
    ):
        level = SecurityLevel.HIGH
    elif PackageRiskCategory.NETWORK_ACCESS in risks or len(risks) >= 2:
        level = SecurityLevel.MEDIUM
    elif risks:
        level = SecurityLevel.LOW
    else:
        level = SecurityLevel.LOW  # Default for statistical packages

    return level, risks


def filter_packages_by_security(
    packages: set[str], max_security_level: SecurityLevel
) -> set[str]:
    """
    Filter packages based on maximum allowed security level.

    Args:
        packages: Set of package names to filter
        max_security_level: Maximum allowed security level

    Returns:
        Filtered set of packages
    """
    security_order = [
        SecurityLevel.LOW,
        SecurityLevel.MEDIUM,
        SecurityLevel.HIGH,
        SecurityLevel.CRITICAL,
    ]
    max_index = security_order.index(max_security_level)

    filtered = set()
    for package in packages:
        level, _ = assess_package_security_risk(package)
        if security_order.index(level) <= max_index:
            filtered.add(package)

    return filtered


def get_security_report(packages: set[str]) -> dict:
    """
    Generate a security assessment report for a set of packages.

    Args:
        packages: Set of package names to assess

    Returns:
        Dictionary with security statistics and categorization
    """
    security_stats = dict.fromkeys(SecurityLevel, 0)
    risk_stats = dict.fromkeys(PackageRiskCategory, 0)
    flagged_packages = {level: [] for level in SecurityLevel}

    for package in packages:
        level, risks = assess_package_security_risk(package)
        security_stats[level] += 1
        flagged_packages[level].append(package)

        for risk in risks:
            risk_stats[risk] += 1

    return {
        "total_packages": len(packages),
        "security_levels": {
            level.value: count for level, count in security_stats.items()
        },
        "risk_categories": {risk.value: count for risk, count in risk_stats.items()},
        "flagged_packages": {
            level.value: sorted(pkgs) for level, pkgs in flagged_packages.items()
        },
        "recommendations": _get_security_recommendations(security_stats),
    }


def _get_security_recommendations(
    security_stats: dict[SecurityLevel, int],
) -> list[str]:
    """Generate security recommendations based on package statistics."""
    recommendations = []

    if security_stats[SecurityLevel.HIGH] > 0:
        recommendations.append(
            f"HIGH RISK: {security_stats[SecurityLevel.HIGH]} packages with elevated privileges. "
            "Consider approval workflow for system access packages."
        )

    if security_stats[SecurityLevel.MEDIUM] > 10:
        recommendations.append(
            f"MEDIUM RISK: {security_stats[SecurityLevel.MEDIUM]} packages with network/file access. "
            "Monitor for potential data exfiltration."
        )

    if security_stats[SecurityLevel.LOW] > 0:
        recommendations.append(
            f"LOW RISK: {security_stats[SecurityLevel.LOW]} standard statistical packages. "
            "Generally safe for analytical work."
        )

    return recommendations


# Popular packages based on CRAN download statistics (for prioritization)
TOP_DOWNLOADED_PACKAGES = {
    # Top 50 most downloaded packages (weekly stats)
    "rlang",
    "cli",
    "ggplot2",
    "vctrs",
    "lifecycle",
    "dplyr",
    "ragg",
    "textshaping",
    "tidyselect",
    "devtools",
    "glue",
    "tibble",
    "fansi",
    "utf8",
    "pillar",
    "digest",
    "crayon",
    "withr",
    "R6",
    "magrittr",
    "ellipsis",
    "pkgconfig",
    "stringi",
    "tidyr",
    "readr",
    "purrr",
    "forcats",
    "lubridate",
    "stringr",
    "broom",
    "scales",
    "colorspace",
    "munsell",
    "RColorBrewer",
    "viridisLite",
    "ggrepel",
    "corrplot",
    "cowplot",
    "gridExtra",
    "lattice",
    "MASS",
    "survival",
    "Matrix",
    "nlme",
    "mgcv",
    "boot",
    "cluster",
    "foreign",
    "nnet",
    "rpart",
}


def prioritize_packages_by_popularity(packages: set[str]) -> list[str]:
    """
    Sort packages by popularity (download statistics).

    Args:
        packages: Set of package names

    Returns:
        List of packages sorted by popularity (most popular first)
    """
    popular = []
    standard = []

    for package in packages:
        if package in TOP_DOWNLOADED_PACKAGES:
            popular.append(package)
        else:
            standard.append(package)

    return sorted(popular) + sorted(standard)


if __name__ == "__main__":
    # Example usage
    from package_whitelist_comprehensive import get_comprehensive_package_whitelist

    packages = get_comprehensive_package_whitelist()
    report = get_security_report(packages)

    # Configure structured logging for utility
    configure_structured_logging(level="INFO", development_mode=True)

    logger.info(
        "Security Assessment Report",
        report_type="security_assessment",
        total_packages=report["total_packages"],
        security_levels=report["security_levels"],
        risk_categories=report["risk_categories"],
    )

    logger.info(
        "Security assessment completed", recommendations=report["recommendations"]
    )
