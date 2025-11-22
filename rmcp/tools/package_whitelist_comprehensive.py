"""
Comprehensive R Package Whitelist Based on CRAN Task Views and Usage Statistics.

This module defines a systematic, evidence-based whitelist of R packages for statistical
analysis, organized by CRAN task views and validated by download statistics.

Updated: January 2025
Sources: CRAN Task Views, download statistics, security assessment
"""

# Base R packages (always available, built-in)
BASE_R_PACKAGES = {
    "base",
    "stats",
    "graphics",
    "grDevices",
    "utils",
    "datasets",
    "methods",
    "grid",
    "splines",
    "stats4",
    "tools",
    "tcltk",
    "compiler",
    "parallel",
}

# Core infrastructure packages (high download volume, essential)
CORE_INFRASTRUCTURE = {
    # Package management and development
    "devtools",
    "remotes",
    "pak",
    "renv",
    "usethis",
    "pkgbuild",
    "pkgload",
    # Language infrastructure
    "rlang",
    "cli",
    "vctrs",
    "lifecycle",
    "ellipsis",
    "glue",
    "magrittr",
    "crayon",
    "pillar",
    "fansi",
    "utf8",
    # Data structures and utilities
    "tibble",
    "data.table",
    "Matrix",
    "lattice",
    "digest",
    "evaluate",
    "knitr",
    "rmarkdown",
    "yaml",
    "jsonlite",
    "xml2",
    "httr",
    "curl",
    # String and date handling
    "stringr",
    "stringi",
    "lubridate",
    "hms",
    "scales",
}

# Tidyverse ecosystem (most popular data science packages)
TIDYVERSE_ECOSYSTEM = {
    # Core tidyverse
    "tidyverse",
    "dplyr",
    "tidyr",
    "ggplot2",
    "readr",
    "purrr",
    "forcats",
    "tibble",
    "stringr",
    "lubridate",
    # Extended tidyverse
    "broom",
    "modelr",
    "tidymodels",
    "tidyselect",
    "tidytext",
    "dbplyr",
    "dtplyr",
    "googlesheets4",
    "haven",
    "reprex",
    "rvest",
    "googledrive",
    # Visualization extensions
    "ggrepel",
    "ggpubr",
    "gganimate",
    "ggridges",
    "patchwork",
    "cowplot",
    "gridExtra",
    "viridis",
    "RColorBrewer",
    "corrplot",
}

# Machine Learning & Statistical Learning (CRAN Task View)
MACHINE_LEARNING = {
    # Core ML packages
    "caret",
    "mlr3",
    "tidymodels",
    "SuperLearner",
    "h2o",
    "mlbench",
    # Neural networks and deep learning
    "nnet",
    "RSNNS",
    "deepnet",
    "torch",
    "tensorflow",
    "keras",
    # Tree-based methods
    "rpart",
    "tree",
    "party",
    "partykit",
    "randomForest",
    "ranger",
    "randomForestSRC",
    "Rborist",
    "gbm",
    "xgboost",
    "lightgbm",
    "C50",
    # Support vector machines
    "e1071",
    "kernlab",
    "LiblineaR",
    # Regularization
    "glmnet",
    "lars",
    "grplasso",
    "ncvreg",
    "elasticnet",
    "penalized",
    # Boosting
    "mboost",
    "ada",
    "adabag",
    # Clustering
    "cluster",
    "factoextra",
    "NbClust",
    "fpc",
    "dbscan",
    "Mclust",
    # Bayesian ML
    "BART",
    "BayesTree",
    "tgp",
    # Ensemble methods
    "extraTrees",
    "Boruta",
    "varSelRF",
    # Performance evaluation
    "mlr3measures",
    "yardstick",
    "MLmetrics",
    "pROC",
    "ROCR",
    # Explainable AI
    "DALEX",
    "iml",
    "fastshap",
    "shapr",
    "lime",
    "breakDown",
    # Feature selection
    "FSelector",
    "RReliefF",
}

# Econometrics (CRAN Task View)
ECONOMETRICS = {
    # Core econometrics
    "AER",
    "car",
    "lmtest",
    "sandwich",
    "systemfit",
    "plm",
    "quantreg",
    # Instrumental variables
    "ivreg",
    "ivpack",
    "REndo",
    # Panel data
    "panelvar",
    "lfe",
    "fixest",
    # Time series econometrics
    "vars",
    "urca",
    "tseries",
    "dynlm",
    "dyn",
    "forecast",
    # Causal inference
    "did",
    "DoubleML",
    "grf",
    "rdrobust",
    "Matching",
    "MatchIt",
    "CausalImpact",
    "Synth",
    "tidysynth",
    # Choice models
    "mlogit",
    "mnlogit",
    "nnet",
    "VGAM",
    "gmnl",
    "apollo",
    "mixl",
    # Limited dependent variables
    "censReg",
    "sampleSelection",
    "betareg",
    "brglm",
    "crch",
    # Bayesian econometrics
    "bayesm",
    "MCMCpack",
    "BVAR",
    # Microeconomics
    "micEcon",
    "micEconAids",
    "micEconCES",
    "micEconSNQP",
    # Effects and margins
    "effects",
    "marginaleffects",
    "margins",
    # Spatial econometrics
    "spatialreg",
    "spdep",
    "spgm",
    # Machine learning econometrics
    "hdm",
    "glmnet",
}

# Time Series Analysis (CRAN Task View)
TIME_SERIES = {
    # Core time series
    "ts",
    "zoo",
    "xts",
    "tsibble",
    "lubridate",
    "timeDate",
    "tis",
    # Forecasting
    "forecast",
    "fable",
    "prophet",
    "smooth",
    "ets",
    "bsts",
    # Time series features and analysis
    "feasts",
    "tsfeatures",
    "TSdist",
    "dtw",
    "wavelets",
    # ARIMA and state space
    "arima2",
    "KFAS",
    "dlm",
    "MARSS",
    # Multivariate time series
    "vars",
    "MTS",
    "VARsignR",
    "BVAR",
    "BigVAR",
    # Nonlinear time series
    "tsDyn",
    "nonlinearTseries",
    "tseriesChaos",
    "NTS",
    # Change point detection
    "changepoint",
    "strucchange",
    "trend",
    "bcp",
    # Frequency domain
    "wavethresh",
    "multitaper",
    "bspec",
    # Decomposition
    "seasonal",
    "x13binary",
    "stlplus",
    "Rssa",
    "EMD",
    # Missing data imputation
    "imputeTS",
    # Machine learning for time series
    "nnfor",
    "TSdeeplearning",
    "TSLSTM",
    # High frequency data
    "highfrequency",
    "RcppRoll",
    # Financial time series
    "quantmod",
    "PerformanceAnalytics",
    "TTR",
    "RQuantLib",
    "rugarch",
    "rmgarch",
    "fGarch",
    "ccgarch",
}

# Bayesian Inference (CRAN Task View)
BAYESIAN_INFERENCE = {
    # Core Bayesian packages
    "coda",
    "mcmc",
    "MCMCpack",
    "boa",
    "bayesplot",
    # Modern Bayesian frameworks
    "rstan",
    "rstanarm",
    "brms",
    "nimble",
    "rjags",
    "R2WinBUGS",
    "greta",
    "tensorflow",
    # Bayes factors and model comparison
    "BayesFactor",
    "BMA",
    "BMS",
    "bain",
    "BayesVarSel",
    "bridgesampling",
    # Approximate Bayesian computation
    "abc",
    "abcrf",
    "EasyABC",
    # Specialized Bayesian models
    "arm",
    "bayesm",
    "BACCO",
    "LaplacesDemon",
    "BayesianTools",
    # Bayesian machine learning
    "BART",
    "bartMachine",
    "dbarts",
    "BayesTree",
    # Spatial Bayesian models
    "CARBayes",
    "spBayes",
    "spTimer",
    # Time series Bayesian
    "bayesforecast",
    "BVAR",
    "bayesDccGarch",
    # Causal inference
    "bartCause",
    "bama",
    "BayesCACE",
}

# Survival Analysis (CRAN Task View)
SURVIVAL_ANALYSIS = {
    # Core survival
    "survival",
    "rms",
    "Hmisc",
    # Extended survival modeling
    "flexsurv",
    "flexsurvcure",
    "eha",
    "muhaz",
    "polspline",
    # Competing risks
    "cmprsk",
    "riskRegression",
    "crrSC",
    "etm",
    # Multistate models
    "mstate",
    "msm",
    "flexmsm",
    "p3state",
    # Machine learning survival
    "randomForestSRC",
    "ranger",
    "gbm",
    "glmnet",
    "penalized",
    # Frailty models
    "frailtypack",
    "frailtyHL",
    "coxme",
    # Bayesian survival
    "rstanarm",
    "JMbayes",
    "BMA",
    # Time-varying effects
    "timereg",
    "dynpred",
    # Visualization and evaluation
    "survminer",
    "ggsurvplot",
    "pec",
    "timeROC",
    "risksetROC",
    # Joint modeling
    "JM",
    "joineR",
}

# Spatial Data Analysis (CRAN Task View Selection)
SPATIAL_ANALYSIS = {
    # Core spatial
    "sp",
    "sf",
    "raster",
    "terra",
    "stars",
    # Spatial statistics
    "gstat",
    "automap",
    "geoR",
    "fields",
    "RandomFields",
    # Spatial econometrics
    "spdep",
    "spatialreg",
    "spgm",
    # Visualization
    "tmap",
    "leaflet",
    "ggmap",
    "mapview",
    "cartography",
    # Point pattern analysis
    "spatstat",
    "maptools",
    "PBSmapping",
}

# Optimization and Numerical Methods
OPTIMIZATION = {
    # Core optimization
    "optim",
    "optimx",
    "nloptr",
    "Rsolnp",
    "DEoptim",
    "GA",
    # Linear programming
    "lpSolve",
    "Rmosek",
    "gurobi",
    # Nonlinear optimization
    "minqa",
    "ucminf",
    "Rcgmin",
    "Rvmmin",
    # Global optimization
    "GenSA",
    "rgenoud",
    "hydroPSO",
    # Mathematical programming
    "ROI",
    "ompr",
    "CVXR",
}

# Meta-Analysis
META_ANALYSIS = {
    "meta",
    "metafor",
    "rmeta",
    "netmeta",
    "gemtc",
    "BayesMfSurv",
    "metacor",
    "metaSEM",
    "psychmeta",
    "weightr",
}

# Clinical Trials and Medical Statistics
CLINICAL_TRIALS = {
    "gsDesign",
    "TEQR",
    "Hmisc",
    "epitools",
    "epi",
    "survival",
    "coin",
    "exact2x2",
    "fisher.test",
    "mcnemar.test",
}

# High Performance Computing
HIGH_PERFORMANCE = {
    "parallel",
    "foreach",
    "doParallel",
    "doMC",
    "snow",
    "Rmpi",
    "future",
    "furrr",
    "RcppParallel",
    "bigmemory",
    "ff",
    "biglm",
}

# Robust Statistical Methods
ROBUST_STATISTICS = {
    "robust",
    "robustbase",
    "MASS",
    "quantreg",
    "WRS2",
    "coin",
    "trimcluster",
    "cluster",
    "fpc",
    "robCompositions",
}

# Missing Data Analysis
MISSING_DATA = {
    "mice",
    "VIM",
    "Hmisc",
    "Amelia",
    "missForest",
    "imputeTS",
    "RANN",
    "naniar",
    "finalfit",
    "mi",
}

# Natural Language Processing
NLP_TEXT_MINING = {
    "tm",
    "text",
    "tidytext",
    "quanteda",
    "openNLP",
    "koRpus",
    "stringdist",
    "RecordLinkage",
    "textclean",
    "qdap",
}

# Data Import/Export
DATA_IO = {
    # Database connectivity
    "DBI",
    "RMySQL",
    "RPostgreSQL",
    "RSQLite",
    "odbc",
    "RODBC",
    # File formats
    "readr",
    "readxl",
    "openxlsx",
    "writexl",
    "haven",
    "foreign",
    "R.matlab",
    "ncdf4",
    "XML",
    "jsonlite",
    "yaml",
    # Web APIs
    "httr",
    "curl",
    "rvest",
    "RCurl",
    "xml2",
}

# Experimental Design
EXPERIMENTAL_DESIGN = {
    "DoE.base",
    "FrF2",
    "planor",
    "conf.design",
    "OptimalDesign",
    "crossdes",
    "AlgDesign",
    "agricolae",
    "dae",
}

# Network Analysis
NETWORK_ANALYSIS = {
    "igraph",
    "network",
    "sna",
    "statnet",
    "tidygraph",
    "ggraph",
    "networkD3",
    "visNetwork",
    "Rgraphviz",
}


# Combine all categories into comprehensive whitelist
def get_comprehensive_package_whitelist():
    """
    Return a comprehensive set of R packages based on CRAN task views and usage statistics.

    Returns:
        set: Comprehensive set of approved R packages
    """
    comprehensive_set = set()

    # Add all package categories
    for package_set in [
        BASE_R_PACKAGES,
        CORE_INFRASTRUCTURE,
        TIDYVERSE_ECOSYSTEM,
        MACHINE_LEARNING,
        ECONOMETRICS,
        TIME_SERIES,
        BAYESIAN_INFERENCE,
        SURVIVAL_ANALYSIS,
        SPATIAL_ANALYSIS,
        OPTIMIZATION,
        META_ANALYSIS,
        CLINICAL_TRIALS,
        HIGH_PERFORMANCE,
        ROBUST_STATISTICS,
        MISSING_DATA,
        NLP_TEXT_MINING,
        DATA_IO,
        EXPERIMENTAL_DESIGN,
        NETWORK_ANALYSIS,
    ]:
        comprehensive_set.update(package_set)

    return comprehensive_set


def get_package_categories():
    """
    Return dictionary mapping category names to package sets.

    Returns:
        dict: Category name -> set of packages
    """
    return {
        "base_r": BASE_R_PACKAGES,
        "core_infrastructure": CORE_INFRASTRUCTURE,
        "tidyverse": TIDYVERSE_ECOSYSTEM,
        "machine_learning": MACHINE_LEARNING,
        "econometrics": ECONOMETRICS,
        "time_series": TIME_SERIES,
        "bayesian": BAYESIAN_INFERENCE,
        "survival": SURVIVAL_ANALYSIS,
        "spatial": SPATIAL_ANALYSIS,
        "optimization": OPTIMIZATION,
        "meta_analysis": META_ANALYSIS,
        "clinical_trials": CLINICAL_TRIALS,
        "high_performance": HIGH_PERFORMANCE,
        "robust_stats": ROBUST_STATISTICS,
        "missing_data": MISSING_DATA,
        "nlp_text": NLP_TEXT_MINING,
        "data_io": DATA_IO,
        "experimental_design": EXPERIMENTAL_DESIGN,
        "network_analysis": NETWORK_ANALYSIS,
    }


# For backward compatibility
ALLOWED_R_PACKAGES = get_comprehensive_package_whitelist()

if __name__ == "__main__":
    # Print statistics
    categories = get_package_categories()
    total_packages = len(ALLOWED_R_PACKAGES)

    print("Comprehensive R Package Whitelist Statistics:")
    print(f"Total packages: {total_packages}")
    print("\nPackages by category:")
    for category, packages in sorted(categories.items()):
        print(f"  {category}: {len(packages)} packages")

    print("\nFirst 10 packages alphabetically:")
    for pkg in sorted(ALLOWED_R_PACKAGES)[:10]:
        print(f"  {pkg}")
