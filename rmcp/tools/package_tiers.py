"""
Tiered R Package Permission System for RMCP.

This module implements a tiered approach to R package permissions, balancing
security with usability by categorizing packages into permission tiers.
"""

from enum import Enum

from ..logging_config import configure_structured_logging, get_logger

logger = get_logger(__name__)

from .package_security import (
    TOP_DOWNLOADED_PACKAGES,
    SecurityLevel,
    assess_package_security_risk,
)
from .package_whitelist_comprehensive import (
    BASE_R_PACKAGES,
    BAYESIAN_INFERENCE,
    CORE_INFRASTRUCTURE,
    ECONOMETRICS,
    MACHINE_LEARNING,
    OPTIMIZATION,
    SPATIAL_ANALYSIS,
    SURVIVAL_ANALYSIS,
    TIDYVERSE_ECOSYSTEM,
    TIME_SERIES,
)


class PackageTier(Enum):
    """Package permission tiers for different security and approval levels."""

    AUTO_APPROVED = "auto_approved"  # Tier 1: Automatically approved, core packages
    USER_APPROVAL = "user_approval"  # Tier 2: Requires user approval, extended packages
    ADMIN_APPROVAL = (
        "admin_approval"  # Tier 3: Requires admin approval, specialized packages
    )
    BLOCKED = "blocked"  # Tier 4: Blocked packages, security risks


def get_package_tier(package_name: str) -> PackageTier:
    """
    Determine the permission tier for a given R package.

    Args:
        package_name: Name of the R package

    Returns:
        PackageTier enum value
    """
    # Assess security risk
    security_level, risk_categories = assess_package_security_risk(package_name)

    # Tier 1: Auto-approved (core statistical packages)
    if package_name in get_tier1_packages():
        return PackageTier.AUTO_APPROVED

    # Tier 4: Blocked (high security risk packages not in whitelist)
    if (
        security_level == SecurityLevel.HIGH
        and package_name in get_high_risk_packages()
    ):
        return PackageTier.BLOCKED

    # Tier 3: Admin approval (specialized or risky packages)
    if security_level == SecurityLevel.HIGH or package_name in get_tier3_packages():
        return PackageTier.ADMIN_APPROVAL

    # Tier 2: User approval (extended packages)
    return PackageTier.USER_APPROVAL


def get_tier1_packages() -> set[str]:
    """
    Get Tier 1 packages: Auto-approved core packages.

    Returns:
        Set of package names that are automatically approved
    """
    # Core packages that are essential and low-risk
    tier1 = set()

    # Base R packages (always safe)
    tier1.update(BASE_R_PACKAGES)

    # Core infrastructure (essential for R ecosystem)
    core_safe = {
        "rlang",
        "cli",
        "glue",
        "magrittr",
        "crayon",
        "pillar",
        "fansi",
        "utf8",
        "lifecycle",
        "vctrs",
        "ellipsis",
        "digest",
        "tibble",
    }
    tier1.update(core_safe & CORE_INFRASTRUCTURE)

    # Essential tidyverse (data manipulation core)
    tidyverse_core = {
        "dplyr",
        "tidyr",
        "ggplot2",
        "readr",
        "tibble",
        "stringr",
        "forcats",
        "lubridate",
        "purrr",
        "broom",
    }
    tier1.update(tidyverse_core & TIDYVERSE_ECOSYSTEM)

    # Essential statistical packages
    stats_core = {
        "MASS",
        "survival",
        "boot",
        "cluster",
        "lattice",
        "Matrix",
        "nlme",
        "mgcv",
        "foreign",
        "nnet",
        "rpart",
    }
    tier1.update(stats_core)

    # Popular visualization
    viz_safe = {"scales", "colorspace", "RColorBrewer", "viridisLite", "corrplot"}
    tier1.update(viz_safe)

    return tier1


def get_tier2_packages() -> set[str]:
    """
    Get Tier 2 packages: User approval required.

    Returns:
        Set of package names requiring user approval
    """
    # Most comprehensive packages that are medium risk
    tier2 = set()

    # Extended tidyverse
    tier2.update(TIDYVERSE_ECOSYSTEM - get_tier1_packages())

    # Core machine learning (popular, well-established)
    ml_popular = {
        "caret",
        "randomForest",
        "rpart",
        "tree",
        "e1071",
        "cluster",
        "glmnet",
        "gbm",
        "BART",
        "ranger",
        "mlr3",
        "tidymodels",
    }
    tier2.update(ml_popular & MACHINE_LEARNING)

    # Core econometrics
    econ_popular = {
        "AER",
        "plm",
        "lmtest",
        "sandwich",
        "car",
        "systemfit",
        "vars",
        "forecast",
        "urca",
        "quantreg",
    }
    tier2.update(econ_popular & ECONOMETRICS)

    # Core time series
    ts_popular = {
        "zoo",
        "xts",
        "forecast",
        "tseries",
        "urca",
        "vars",
        "fable",
        "feasts",
        "tsibble",
    }
    tier2.update(ts_popular & TIME_SERIES)

    # Core Bayesian (established packages)
    bayes_popular = {"coda", "MCMCpack", "BayesFactor", "arm", "boa", "rstan", "brms"}
    tier2.update(bayes_popular & BAYESIAN_INFERENCE)

    # Popular packages (high download count = community validated)
    popular_safe = TOP_DOWNLOADED_PACKAGES & (
        MACHINE_LEARNING | ECONOMETRICS | TIME_SERIES | SURVIVAL_ANALYSIS
    )
    tier2.update(popular_safe)

    return tier2


def get_tier3_packages() -> set[str]:
    """
    Get Tier 3 packages: Admin approval required.

    Returns:
        Set of package names requiring admin approval
    """
    # Specialized or higher-risk packages
    tier3 = set()

    # Advanced/specialized packages
    tier3.update(SPATIAL_ANALYSIS)  # GIS packages often have external dependencies
    tier3.update(OPTIMIZATION)  # Mathematical optimization

    # Advanced ML packages (less common, more specialized)
    ml_advanced = {
        "xgboost",
        "lightgbm",
        "h2o",
        "tensorflow",
        "torch",
        "keras",
        "deepnet",
        "RSNNS",
        "kernlab",
    }
    tier3.update(ml_advanced & MACHINE_LEARNING)

    # Advanced Bayesian (MCMC samplers, specialized)
    bayes_advanced = {
        "rstan",
        "rstanarm",
        "brms",
        "nimble",
        "rjags",
        "R2WinBUGS",
        "LaplacesDemon",
        "BayesianTools",
    }
    tier3.update(bayes_advanced & BAYESIAN_INFERENCE)

    # Development and system packages
    dev_packages = {
        "devtools",
        "remotes",
        "pak",
        "usethis",
        "pkgbuild",
        "pkgload",
        "rcmdcheck",
        "roxygen2",
    }
    tier3.update(dev_packages)

    # Network and web packages
    web_packages = {
        "httr",
        "httr2",
        "curl",
        "RCurl",
        "rvest",
        "xml2",
        "jsonlite",
        "plumber",
        "shiny",
        "httpuv",
    }
    tier3.update(web_packages)

    return tier3


def get_high_risk_packages() -> set[str]:
    """
    Get packages considered high-risk for security.

    Returns:
        Set of package names with elevated security risks
    """
    return {
        # System access
        "RAppArmor",
        "unix",
        "processx",
        "callr",
        "sys",
        # Code execution and compilation
        "Rcpp",
        "RcppArmadillo",
        "inline",
        "compiler",
        "reticulate",
        "JuliaCall",
        "RJulia",
        "V8",
        "rJava",
        # External system dependencies
        "RMySQL",
        "RPostgreSQL",
        "ROracle",
        "RODBC",
        "Cairo",
        "tkrplot",
        "tcltk",
        "Rgtk2",
        "cairoDevice",
        "rgl",
        "rgdal",
        "rgeos",
    }


def get_packages_by_tier() -> dict[PackageTier, set[str]]:
    """
    Get packages organized by permission tier.

    Returns:
        Dictionary mapping tiers to package sets
    """
    return {
        PackageTier.AUTO_APPROVED: get_tier1_packages(),
        PackageTier.USER_APPROVAL: get_tier2_packages(),
        PackageTier.ADMIN_APPROVAL: get_tier3_packages(),
        PackageTier.BLOCKED: get_high_risk_packages(),
    }


def get_tier_statistics() -> dict:
    """
    Get statistics about package distribution across tiers.

    Returns:
        Dictionary with tier statistics
    """
    tiers = get_packages_by_tier()

    stats = {}
    for tier, packages in tiers.items():
        stats[tier.value] = {
            "count": len(packages),
            "examples": sorted(packages)[:5],
        }

    total_packages = sum(len(packages) for packages in tiers.values())
    stats["total"] = total_packages

    return stats


def check_package_permission(package_name: str) -> dict:
    """
    Check the permission requirements for a specific package.

    Args:
        package_name: Name of the R package

    Returns:
        Dictionary with permission information
    """
    tier = get_package_tier(package_name)
    security_level, risk_categories = assess_package_security_risk(package_name)

    return {
        "package": package_name,
        "tier": tier.value,
        "security_level": security_level.value,
        "risk_categories": [risk.value for risk in risk_categories],
        "auto_approved": tier == PackageTier.AUTO_APPROVED,
        "requires_approval": tier
        in [PackageTier.USER_APPROVAL, PackageTier.ADMIN_APPROVAL],
        "blocked": tier == PackageTier.BLOCKED,
        "description": _get_tier_description(tier),
    }


def _get_tier_description(tier: PackageTier) -> str:
    """Get human-readable description of a permission tier."""
    descriptions = {
        PackageTier.AUTO_APPROVED: "Core package, automatically approved for use",
        PackageTier.USER_APPROVAL: "Extended package, requires user approval",
        PackageTier.ADMIN_APPROVAL: "Specialized package, requires admin approval",
        PackageTier.BLOCKED: "High-risk package, blocked for security",
    }
    return descriptions[tier]


if __name__ == "__main__":
    # Configure structured logging for utility
    configure_structured_logging(level="INFO", development_mode=True)

    # Print tier statistics using structured logging
    stats = get_tier_statistics()

    logger.info(
        "Package Tier Statistics",
        report_type="tier_statistics",
        total_packages=stats["total"],
    )

    for tier_name, tier_stats in stats.items():
        if tier_name != "total":
            logger.info(
                "Tier details",
                tier=tier_name.upper(),
                count=tier_stats["count"],
                examples=tier_stats["examples"],
            )

    # Test specific packages
    test_packages = ["ggplot2", "xgboost", "devtools", "rJava"]
    logger.info("Package Permission Examples")

    for pkg in test_packages:
        info = check_package_permission(pkg)
        logger.info(
            "Package permission check",
            package=pkg,
            tier=info["tier"],
            description=info["description"],
        )
