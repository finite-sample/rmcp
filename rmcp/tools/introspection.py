"""
R Environment Introspection Tools.

This module provides MCP tools for introspecting R environments, inspired by mcptools.
These tools allow AI assistants to understand the current state of R sessions,
including workspace objects, loaded packages, and data structures.

Key features:
- List objects in R workspace
- Inspect data structure and content
- Browse loaded packages and functions
- Get session metadata and environment info
- Search for objects and documentation

These tools enhance the AI assistant's ability to provide context-aware
statistical analysis recommendations and data manipulation suggestions.
"""

from typing import Any

from ..core.context import Context
from ..registries.tools import tool


@tool(
    name="list_r_objects",
    description="List all objects in the current R workspace/session",
    input_schema={
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "R session ID (optional, uses default if not specified)",
            },
            "pattern": {
                "type": "string",
                "description": "Optional regex pattern to filter object names",
            },
            "include_hidden": {
                "type": "boolean",
                "description": "Include hidden objects (starting with .)",
                "default": False,
            },
            "sort_by": {
                "type": "string",
                "enum": ["name", "size", "class", "created"],
                "description": "Sort objects by attribute",
                "default": "name",
            },
        },
    },
)
async def list_r_objects(context: Context, params: dict[str, Any]) -> dict[str, Any]:
    """
    List all objects in the R workspace with metadata.

    This tool provides an overview of what data, models, and variables
    are available in the current R session, helping AI assistants understand
    the analysis context.
    """
    session_id = params.get("session_id")
    pattern = params.get("pattern", "")
    include_hidden = params.get("include_hidden", False)
    sort_by = params.get("sort_by", "name")

    # R script to list objects with metadata
    r_script = f"""
    # Set parameters
    pattern <- "{pattern}"
    include_hidden <- {str(include_hidden).lower()}
    sort_by <- "{sort_by}"

    # Get all objects
    if (include_hidden) {{
        all_objects <- ls(envir = .GlobalEnv, all.names = TRUE)
    }} else {{
        all_objects <- ls(envir = .GlobalEnv)
    }}

    # Filter by pattern if provided
    if (nchar(pattern) > 0) {{
        all_objects <- all_objects[grepl(pattern, all_objects)]
    }}

    # Get detailed information for each object
    object_info <- list()
    for (obj_name in all_objects) {{
        tryCatch({{
            obj <- get(obj_name, envir = .GlobalEnv)

            # Basic metadata
            info <- list(
                name = obj_name,
                class = class(obj)[1],
                type = typeof(obj),
                mode = mode(obj),
                length = length(obj),
                size_bytes = as.numeric(object.size(obj))
            )

            # Additional info based on object type
            if (is.data.frame(obj)) {{
                info$rows <- nrow(obj)
                info$cols <- ncol(obj)
                info$columns <- colnames(obj)
            }} else if (is.matrix(obj)) {{
                info$dims <- dim(obj)
                info$rows <- nrow(obj)
                info$cols <- ncol(obj)
            }} else if (is.list(obj)) {{
                info$elements <- length(obj)
                info$element_names <- names(obj)
            }} else if (is.vector(obj) && length(obj) > 0) {{
                info$first_few <- head(obj, 3)
                if (is.numeric(obj)) {{
                    info$min <- min(obj, na.rm = TRUE)
                    info$max <- max(obj, na.rm = TRUE)
                    info$mean <- mean(obj, na.rm = TRUE)
                }}
            }}

            # Check if it's a model object
            if ("lm" %in% class(obj) || "glm" %in% class(obj) || "aov" %in% class(obj)) {{
                info$is_model <- TRUE
                info$formula <- deparse(formula(obj))
                if ("lm" %in% class(obj) || "glm" %in% class(obj)) {{
                    info$r_squared <- summary(obj)$r.squared
                }}
            }}

            object_info[[obj_name]] <- info
        }}, error = function(e) {{
            object_info[[obj_name]] <- list(
                name = obj_name,
                error = e$message
            )
        }})
    }}

    # Sort objects
    if (sort_by == "size") {{
        object_info <- object_info[order(sapply(object_info, function(x) x$size_bytes %||% 0), decreasing = TRUE)]
    }} else if (sort_by == "class") {{
        object_info <- object_info[order(sapply(object_info, function(x) x$class %||% ""))]
    }} else {{
        object_info <- object_info[order(names(object_info))]
    }}

    # Summary statistics
    total_objects <- length(object_info)
    total_size <- sum(sapply(object_info, function(x) x$size_bytes %||% 0))

    class_counts <- table(sapply(object_info, function(x) x$class %||% "unknown"))

    result <- list(
        objects = object_info,
        summary = list(
            total_objects = total_objects,
            total_size_bytes = total_size,
            class_distribution = as.list(class_counts),
            session_info = list(
                search_pattern = pattern,
                include_hidden = include_hidden,
                sort_by = sort_by
            )
        )
    )
    """

    args = {"session_id": session_id}

    try:
        # Execute with session support if available
        result = await context.execute_r_with_session(r_script, args, use_session=True)

        return {
            "objects": result.get("objects", {}),
            "summary": result.get("summary", {}),
            "session_id": session_id,
            "success": True,
        }

    except Exception as e:
        await context.error(f"Failed to list R objects: {e}")
        return {"objects": {}, "summary": {}, "error": str(e), "success": False}


@tool(
    name="inspect_r_object",
    description="Get detailed information about a specific R object",
    input_schema={
        "type": "object",
        "properties": {
            "object_name": {
                "type": "string",
                "description": "Name of the R object to inspect",
            },
            "session_id": {"type": "string", "description": "R session ID (optional)"},
            "include_summary": {
                "type": "boolean",
                "description": "Include statistical summary for data objects",
                "default": True,
            },
            "include_structure": {
                "type": "boolean",
                "description": "Include object structure details",
                "default": True,
            },
            "max_preview_rows": {
                "type": "integer",
                "description": "Maximum rows to preview for data frames",
                "default": 10,
            },
        },
        "required": ["object_name"],
    },
)
async def inspect_r_object(context: Context, params: dict[str, Any]) -> dict[str, Any]:
    """
    Inspect a specific R object in detail.

    This tool provides comprehensive information about R objects,
    including structure, content preview, and statistical summaries
    where applicable.
    """
    object_name = params["object_name"]
    session_id = params.get("session_id")
    include_summary = params.get("include_summary", True)
    include_structure = params.get("include_structure", True)
    max_preview_rows = params.get("max_preview_rows", 10)

    r_script = f"""
    object_name <- "{object_name}"
    include_summary <- {str(include_summary).lower()}
    include_structure <- {str(include_structure).lower()}
    max_preview_rows <- {max_preview_rows}

    # Check if object exists
    if (!exists(object_name, envir = .GlobalEnv)) {{
        result <- list(
            exists = FALSE,
            error = paste("Object", object_name, "not found in workspace")
        )
    }} else {{
        obj <- get(object_name, envir = .GlobalEnv)

        # Basic information
        info <- list(
            exists = TRUE,
            name = object_name,
            class = class(obj),
            type = typeof(obj),
            mode = mode(obj),
            length = length(obj),
            size_bytes = as.numeric(object.size(obj)),
            attributes = attributes(obj)
        )

        # Structure information
        if (include_structure) {{
            info$structure <- capture.output(str(obj))
        }}

        # Detailed analysis based on object type
        if (is.data.frame(obj)) {{
            info$data_frame_info <- list(
                rows = nrow(obj),
                cols = ncol(obj),
                column_names = colnames(obj),
                column_types = sapply(obj, class),
                row_names_sample = head(rownames(obj), 5)
            )

            # Preview data
            if (nrow(obj) > 0) {{
                preview_rows <- min(max_preview_rows, nrow(obj))
                info$preview <- head(obj, preview_rows)
            }}

            # Summary statistics
            if (include_summary) {{
                numeric_cols <- sapply(obj, is.numeric)
                if (any(numeric_cols)) {{
                    info$numeric_summary <- summary(obj[numeric_cols])
                }}

                factor_cols <- sapply(obj, is.factor)
                if (any(factor_cols)) {{
                    info$factor_summary <- lapply(obj[factor_cols], function(x) table(x, useNA = "ifany"))
                }}
            }}

        }} else if (is.matrix(obj)) {{
            info$matrix_info <- list(
                dimensions = dim(obj),
                dimnames = dimnames(obj)
            )

            if (include_summary && is.numeric(obj)) {{
                info$summary_stats <- list(
                    min = min(obj, na.rm = TRUE),
                    max = max(obj, na.rm = TRUE),
                    mean = mean(obj, na.rm = TRUE),
                    median = median(obj, na.rm = TRUE)
                )
            }}

        }} else if (is.list(obj)) {{
            info$list_info <- list(
                elements = length(obj),
                element_names = names(obj),
                element_classes = sapply(obj, class)
            )

            # Preview first few elements
            if (length(obj) > 0) {{
                preview_count <- min(3, length(obj))
                info$element_preview <- obj[1:preview_count]
            }}

        }} else if (is.vector(obj)) {{
            info$vector_info <- list(
                length = length(obj),
                names = names(obj)
            )

            # Preview values
            if (length(obj) > 0) {{
                preview_count <- min(10, length(obj))
                info$value_preview <- obj[1:preview_count]

                if (is.numeric(obj) && include_summary) {{
                    info$summary_stats <- list(
                        min = min(obj, na.rm = TRUE),
                        max = max(obj, na.rm = TRUE),
                        mean = mean(obj, na.rm = TRUE),
                        median = median(obj, na.rm = TRUE),
                        sd = sd(obj, na.rm = TRUE),
                        na_count = sum(is.na(obj))
                    )
                }}
            }}
        }}

        # Special handling for model objects
        if ("lm" %in% class(obj) || "glm" %in% class(obj)) {{
            model_summary <- summary(obj)
            info$model_info <- list(
                formula = deparse(formula(obj)),
                coefficients = coef(obj),
                r_squared = model_summary$r.squared,
                adj_r_squared = model_summary$adj.r.squared,
                residual_se = model_summary$sigma,
                df = model_summary$df,
                call = deparse(obj$call)
            )
        }}

        result <- info
    }}
    """

    args = {"object_name": object_name}

    try:
        result = await context.execute_r_with_session(r_script, args, use_session=True)

        return {**result, "session_id": session_id, "success": True}

    except Exception as e:
        await context.error(f"Failed to inspect R object '{object_name}': {e}")
        return {"exists": False, "error": str(e), "success": False}


@tool(
    name="list_r_packages",
    description="List loaded R packages and available functions",
    input_schema={
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "R session ID (optional)"},
            "include_base": {
                "type": "boolean",
                "description": "Include base R packages",
                "default": False,
            },
            "package_name": {
                "type": "string",
                "description": "Specific package to inspect (optional)",
            },
        },
    },
)
async def list_r_packages(context: Context, params: dict[str, Any]) -> dict[str, Any]:
    """
    List loaded R packages with their functions and metadata.

    This helps AI assistants understand what statistical functions
    and packages are available in the current R session.
    """
    session_id = params.get("session_id")
    include_base = params.get("include_base", False)
    package_name = params.get("package_name")

    r_script = f"""
    include_base <- {str(include_base).lower()}
    specific_package <- "{package_name or ""}"

    # Get loaded packages
    loaded_packages <- search()

    # Filter out non-package items
    package_items <- loaded_packages[grepl("^package:", loaded_packages)]
    package_names <- gsub("^package:", "", package_items)

    # Filter base packages if requested
    if (!include_base) {{
        base_packages <- c("base", "stats", "graphics", "grDevices", "utils", "datasets", "methods")
        package_names <- package_names[!package_names %in% base_packages]
    }}

    # Filter to specific package if requested
    if (nchar(specific_package) > 0) {{
        package_names <- package_names[package_names == specific_package]
    }}

    # Get detailed info for each package
    package_info <- list()

    for (pkg in package_names) {{
        tryCatch({{
            # Get package description
            desc <- packageDescription(pkg)

            # Get exported functions
            exports <- ls(paste0("package:", pkg))

            # Categorize functions
            functions <- exports[sapply(exports, function(x) is.function(get(x, paste0("package:", pkg))))]
            datasets <- exports[sapply(exports, function(x) is.data.frame(get(x, paste0("package:", pkg))) || is.matrix(get(x, paste0("package:", pkg))))]

            package_info[[pkg]] <- list(
                name = pkg,
                title = desc$Title %||% "No title",
                version = desc$Version %||% "Unknown",
                description = desc$Description %||% "No description",
                functions = functions,
                datasets = datasets,
                total_exports = length(exports),
                loaded_from = paste0("package:", pkg)
            )
        }}, error = function(e) {{
            package_info[[pkg]] <- list(
                name = pkg,
                error = e$message
            )
        }})
    }}

    result <- list(
        packages = package_info,
        summary = list(
            total_packages = length(package_info),
            include_base = include_base,
            specific_package = specific_package,
            session_search_path = search()
        )
    )
    """

    args: dict[str, Any] = {}

    try:
        result = await context.execute_r_with_session(r_script, args, use_session=True)

        return {**result, "session_id": session_id, "success": True}

    except Exception as e:
        await context.error(f"Failed to list R packages: {e}")
        return {"packages": {}, "summary": {}, "error": str(e), "success": False}


@tool(
    name="get_r_session_info",
    description="Get comprehensive information about the R session",
    input_schema={
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "R session ID (optional)"}
        },
    },
)
async def get_r_session_info(
    context: Context, params: dict[str, Any]
) -> dict[str, Any]:
    """
    Get comprehensive information about the R session environment.

    This provides AI assistants with context about the R environment,
    including version, capabilities, working directory, and session state.
    """
    session_id = params.get("session_id")

    r_script = """
    # Collect comprehensive session information
    session_info <- list(
        # R Version and platform
        r_version = R.version.string,
        platform = R.version$platform,
        arch = R.version$arch,
        os = R.version$os,

        # Session details
        working_directory = getwd(),
        temp_directory = tempdir(),
        user = Sys.getenv("USER"),
        locale = Sys.getlocale(),

        # Memory and performance
        memory_limit = memory.limit(),
        memory_size = memory.size(),

        # Search path and loaded packages
        search_path = search(),
        loaded_namespaces = loadedNamespaces(),

        # Capabilities
        capabilities = capabilities(),

        # Session startup info
        session_start = .rmcp_session_start %||% "Unknown",
        session_id = .rmcp_session_id %||% "stateless",

        # Object counts
        global_objects = length(ls(envir = .GlobalEnv)),
        workspace_size = sum(sapply(ls(envir = .GlobalEnv), function(x) object.size(get(x))))
    )

    # Get available packages (installed)
    available_packages <- installed.packages()
    session_info$installed_packages <- nrow(available_packages)
    session_info$package_versions <- available_packages[, c("Package", "Version")]

    # System information
    session_info$system_info <- Sys.info()

    result <- session_info
    """

    args: dict[str, Any] = {}

    try:
        result = await context.execute_r_with_session(r_script, args, use_session=True)

        # Add RMCP-specific session info if available
        if context.is_r_session_enabled():
            from ..r_session import get_session_manager

            session_manager = get_session_manager()

            rmcp_session_info = await session_manager.get_session_info(
                session_id or context.get_r_session_id() or "default"
            )

            if rmcp_session_info:
                result["rmcp_session"] = rmcp_session_info

        return {**result, "session_id": session_id, "success": True}

    except Exception as e:
        await context.error(f"Failed to get R session info: {e}")
        return {"error": str(e), "success": False}
