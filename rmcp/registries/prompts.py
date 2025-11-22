"""
Prompts registry for MCP server.
Implements mature MCP patterns:
- Templated workflows that teach LLMs tool chaining
- Parameterized prompts with typed arguments
- Statistical analysis playbooks
Following the principle: "Ship prompts as workflows."
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from ..core.context import Context
from ..core.schemas import SchemaError, validate_schema

logger = logging.getLogger(__name__)


class PromptHandler(Protocol):
    """Protocol for prompt handler functions with MCP metadata."""

    _mcp_prompt_name: str
    _mcp_prompt_title: str | None
    _mcp_prompt_description: str | None
    _mcp_prompt_template: str
    _mcp_prompt_arguments_schema: dict[str, Any] | None
    _mcp_prompt_annotations: dict[str, Any] | None

    def __call__(self) -> str: ...


def _paginate_items(
    items: list["PromptDefinition"], cursor: str | None, limit: int | None
) -> tuple[list["PromptDefinition"], str | None]:
    """Return a slice of prompts based on cursor/limit pagination."""
    total_items = len(items)
    start_index = 0
    if cursor is not None:
        if not isinstance(cursor, str):
            raise ValueError("cursor must be a string if provided")
        try:
            start_index = int(cursor)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError("cursor must be an integer string") from exc
        if start_index < 0 or start_index > total_items:
            raise ValueError("cursor is out of range")
    if limit is not None:
        try:
            limit_value = int(limit)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValueError("limit must be an integer") from exc
        if limit_value <= 0:
            raise ValueError("limit must be a positive integer")
    else:
        limit_value = total_items - start_index
    end_index = min(start_index + limit_value, total_items)
    next_cursor = str(end_index) if end_index < total_items else None
    return items[start_index:end_index], next_cursor


@dataclass
class PromptDefinition:
    """Prompt template metadata and content."""

    name: str
    title: str
    description: str
    arguments_schema: dict[str, Any] | None
    template: str
    annotations: dict[str, Any] | None = None


class PromptsRegistry:
    """Registry for MCP prompts with templating support."""

    def __init__(
        self,
        on_list_changed: Callable[[list[str] | None], None] | None = None,
    ):
        self._prompts: dict[str, PromptDefinition] = {}
        self._on_list_changed = on_list_changed

    def register(
        self,
        name: str,
        title: str,
        description: str,
        template: str,
        arguments_schema: dict[str, Any] | None = None,
        annotations: dict[str, Any] | None = None,
    ) -> None:
        """Register a prompt template."""
        if name in self._prompts:
            logger.warning(f"Prompt '{name}' already registered, overwriting")
        self._prompts[name] = PromptDefinition(
            name=name,
            title=title,
            description=description,
            template=template,
            arguments_schema=arguments_schema,
            annotations=annotations or {},
        )
        logger.debug(f"Registered prompt: {name}")
        self._emit_list_changed([name])

    async def list_prompts(
        self,
        context: Context,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """List available prompts for MCP prompts/list."""
        ordered_prompts = sorted(self._prompts.values(), key=lambda prompt: prompt.name)
        page, next_cursor = _paginate_items(ordered_prompts, cursor, limit)
        prompts: list[dict[str, Any]] = []
        for prompt_def in page:
            prompt_info: dict[str, Any] = {
                "name": prompt_def.name,
                "title": prompt_def.title,
                "description": prompt_def.description,
            }
            if prompt_def.arguments_schema:
                prompt_info["argumentsSchema"] = prompt_def.arguments_schema
            if prompt_def.annotations:
                prompt_info["annotations"] = prompt_def.annotations
            prompts.append(prompt_info)
        await context.info(
            "Listed prompts",
            count=len(prompts),
            total=len(ordered_prompts),
            next_cursor=next_cursor,
        )
        response: dict[str, Any] = {"prompts": prompts}
        if next_cursor is not None:
            response["nextCursor"] = next_cursor
        return response

    async def get_prompt(
        self, context: Context, name: str, arguments: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Get a rendered prompt for MCP prompts/get."""
        if name not in self._prompts:
            raise ValueError(f"Unknown prompt: {name}")
        prompt_def = self._prompts[name]
        arguments = arguments or {}
        try:
            # Validate arguments if schema provided
            if prompt_def.arguments_schema:
                validate_schema(
                    arguments, prompt_def.arguments_schema, f"prompt '{name}' arguments"
                )
            # Render template
            rendered_content = self._render_template(prompt_def.template, arguments)
            await context.info(f"Rendered prompt: {name}", arguments=arguments)
            return {
                "messages": [
                    {
                        "role": "user",
                        "content": {"type": "text", "text": rendered_content},
                    }
                ]
            }
        except SchemaError as e:
            await context.error(f"Schema validation failed for prompt '{name}': {e}")
            raise
        except Exception as e:
            await context.error(f"Failed to render prompt '{name}': {e}")
            raise

    def _render_template(self, template: str, arguments: dict[str, Any]) -> str:
        """Render template with arguments using simple string formatting."""
        try:
            # Use simple string formatting for now
            # Could be enhanced with Jinja2 or similar
            return template.format(**arguments)
        except KeyError as e:
            raise ValueError(f"Missing template argument: {e}")
        except Exception as e:
            raise ValueError(f"Template rendering error: {e}")

    def _emit_list_changed(self, item_ids: list[str] | None = None) -> None:
        """Emit list changed notification when available."""
        if not self._on_list_changed:
            return
        try:
            self._on_list_changed(item_ids)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("List changed callback failed for prompts: %s", exc)


def prompt(
    name: str,
    title: str,
    description: str,
    arguments_schema: dict[str, Any] | None = None,
    annotations: dict[str, Any] | None = None,
):
    """
    Decorator to register a prompt template.
    Usage:
        @prompt(
            name="analyze_workflow",
            title="Statistical Analysis Workflow",
            description="Guide for comprehensive statistical analysis",
            arguments_schema={
                "type": "object",
                "properties": {
                    "dataset_name": {"type": "string"},
                    "analysis_type": {"type": "string", "enum": ["descriptive", "inferential", "predictive"]}
                },
                "required": ["dataset_name"]
            }
        )
        def analyze_workflow():
            return '''
            I'll help you analyze the {dataset_name} dataset using {analysis_type} methods.
            Let me start by examining the data structure and then proceed with the analysis.
            '''
    """

    def decorator(func: Callable[[], str]) -> PromptHandler:
        # Extract template content from function
        template_content = func()
        # Store prompt metadata on function
        func._mcp_prompt_name = name
        func._mcp_prompt_title = title
        func._mcp_prompt_description = description
        func._mcp_prompt_template = template_content
        func._mcp_prompt_arguments_schema = arguments_schema
        func._mcp_prompt_annotations = annotations
        return func  # type: ignore

    return decorator


def register_prompt_functions(
    registry: PromptsRegistry, *functions: PromptHandler
) -> None:
    """Register multiple functions decorated with @prompt."""
    for func in functions:
        registry.register(
            name=func._mcp_prompt_name,
            title=func._mcp_prompt_title or func._mcp_prompt_name,
            description=func._mcp_prompt_description
            or f"Prompt template for {func._mcp_prompt_name}",
            template=func._mcp_prompt_template,
            arguments_schema=func._mcp_prompt_arguments_schema,
            annotations=func._mcp_prompt_annotations,
        )


# Built-in statistical analysis workflow prompts
@prompt(
    name="statistical_workflow",
    title="Statistical Analysis Workflow",
    description="Comprehensive workflow for statistical data analysis",
    arguments_schema={
        "type": "object",
        "properties": {
            "dataset_name": {"type": "string"},
            "analysis_goals": {"type": "string"},
            "variables_of_interest": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["dataset_name", "analysis_goals"],
    },
)
def statistical_workflow_prompt():
    return """I'll help you conduct a comprehensive statistical analysis of the {dataset_name} dataset.
Analysis Goals: {analysis_goals}
Variables of Interest: {variables_of_interest}
Let me guide you through a systematic analysis workflow:
**Phase 1: Data Exploration**
1. First, I'll examine the dataset structure and summary statistics
2. Check for missing values, outliers, and data quality issues
3. Visualize distributions and relationships between variables
**Phase 2: Analysis Selection**
Based on your goals and data characteristics, I'll recommend:
- Appropriate statistical tests or models
- Required assumptions and validation steps
- Visualization strategies
**Phase 3: Statistical Analysis**
I'll execute the analysis using appropriate tools and provide:
- Statistical results with interpretation
- Effect sizes and confidence intervals
- Diagnostic plots and assumption checking
**Phase 4: Results & Recommendations**
Finally, I'll summarize:
- Key findings and their practical significance
- Limitations and caveats
- Recommendations for next steps
Let's begin by examining your dataset. Please provide the data or specify how to access it."""


@prompt(
    name="model_diagnostic_workflow",
    title="Model Diagnostics Workflow",
    description="Systematic model validation and diagnostics",
    arguments_schema={
        "type": "object",
        "properties": {
            "model_type": {
                "type": "string",
                "enum": ["linear", "logistic", "time_series", "ml"],
            },
            "focus_areas": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["model_type"],
    },
)
def model_diagnostic_prompt():
    return """I'll help you conduct thorough diagnostics for your {model_type} model.
Focus Areas: {focus_areas}
**Model Diagnostic Workflow**
**1. Residual Analysis**
- Plot residuals vs fitted values
- Check for patterns indicating model misspecification
- Assess homoscedasticity assumptions
**2. Distribution Checks**
- Q-Q plots for normality assessment
- Histogram of residuals
- Statistical tests for distributional assumptions
**3. Influence & Outliers**
- Identify high-leverage points
- Cook's distance for influential observations
- Studentized residuals analysis
**4. Model Assumptions**
- Linearity checks (for linear models)
- Independence verification
- Multicollinearity assessment (VIF)
**5. Predictive Performance**
- Cross-validation results
- Out-of-sample performance metrics
- Calibration plots (for probabilistic models)
**6. Interpretation & Validation**
- Coefficient stability
- Bootstrap confidence intervals
- Sensitivity analysis
Let's start the diagnostic process. Please provide your model results or specify how to access the fitted model."""


@prompt(
    name="regression_diagnostics",
    title="Regression Diagnostics Analysis",
    description="Comprehensive regression modeling with diagnostic plots and validation",
    arguments_schema={
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Name of the dependent variable to predict",
            },
            "predictors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of independent variables for the model",
            },
            "dataset_description": {
                "type": "string",
                "description": "Brief description of your dataset and analysis goals",
            },
            "include_interactions": {
                "type": "boolean",
                "default": False,
                "description": "Whether to consider interaction terms between predictors",
            },
        },
        "required": ["target", "predictors", "dataset_description"],
    },
)
def regression_diagnostics_prompt():
    return """I'll help you perform a comprehensive regression analysis for {target} using predictors: {predictors}.
**Dataset Context**: {dataset_description}
**Analysis Workflow**
**Step 1: Model Setup & Fitting**
- I'll fit a linear regression model: {target} ~ {predictors}
- Check for basic model assumptions and data quality
- Provide model summary with R², coefficients, and significance tests
**Step 2: Regression Diagnostics**
- **Residual Plots**: Check for linearity, homoscedasticity, and outliers
- **Q-Q Plot**: Assess normality of residuals
- **Scale-Location Plot**: Verify constant variance assumption
- **Leverage Plot**: Identify influential observations
**Step 3: Model Validation**
- **Multicollinearity Check**: VIF values for predictors
- **Outlier Analysis**: Cook's distance and standardized residuals
- **Assumption Testing**: Formal tests for normality and homoscedasticity
**Step 4: Results Interpretation**
- **Coefficient Interpretation**: Practical significance of each predictor
- **Model Performance**: Overall fit and predictive ability
- **Diagnostic Summary**: Key findings and recommendations
**Ready to Start**
Please provide your dataset with columns for '{target}' and {predictors}. I'll guide you through each step of the analysis with clear explanations and professional diagnostic plots."""


@prompt(
    name="time_series_forecast",
    title="Time Series Forecasting Analysis",
    description="Complete time series analysis with ARIMA modeling and forecasting",
    arguments_schema={
        "type": "object",
        "properties": {
            "variable_name": {
                "type": "string",
                "description": "Name of the time series variable to forecast",
            },
            "periods_ahead": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "default": 12,
                "description": "Number of periods to forecast into the future",
            },
            "frequency": {
                "type": "string",
                "enum": ["monthly", "quarterly", "yearly", "daily", "weekly"],
                "default": "monthly",
                "description": "Time frequency of your data",
            },
            "dataset_description": {
                "type": "string",
                "description": "Brief description of the time series and forecasting purpose",
            },
            "include_seasonality": {
                "type": "boolean",
                "default": True,
                "description": "Whether to model seasonal patterns",
            },
        },
        "required": ["variable_name", "dataset_description"],
    },
)
def time_series_forecast_prompt():
    return """I'll help you create {periods_ahead}-period forecasts for {variable_name} using advanced time series methods.
**Forecasting Context**: {dataset_description}
**Data Frequency**: {frequency}
**Seasonality**: Will be analyzed based on data patterns
**Time Series Analysis Workflow**
**Phase 1: Data Exploration & Preparation**
- **Time Series Plot**: Visualize trends, seasonality, and patterns
- **Decomposition**: Separate trend, seasonal, and irregular components
- **Stationarity Assessment**: ADF and KPSS tests for unit roots
**Phase 2: Model Identification**
- **ACF/PACF Analysis**: Identify potential ARIMA orders
- **Automatic Model Selection**: Find optimal (p,d,q) parameters
- **Seasonal Component**: Automatically detect and model seasonal patterns if present
**Phase 3: ARIMA Modeling**
- **Model Fitting**: Estimate best ARIMA model parameters
- **Diagnostic Checking**: Residual analysis and model validation
- **Information Criteria**: AIC/BIC for model comparison
**Phase 4: Forecasting & Validation**
- **{periods_ahead}-Period Forecast**: Point forecasts with confidence intervals
- **Forecast Plot**: Visual representation of predictions
- **Accuracy Metrics**: In-sample fit statistics
- **Prediction Intervals**: Uncertainty quantification
**Phase 5: Results & Recommendations**
- **Forecast Interpretation**: What the predictions mean for your context
- **Model Limitations**: Important caveats and assumptions
- **Next Steps**: Suggestions for monitoring and model updates
**Ready to Begin**
Please provide your time series data with:
- **{variable_name}**: The values to forecast
- **Time Index**: Dates or time periods for proper sequencing
I'll handle the technical details and provide clear, actionable forecasting results."""


@prompt(
    name="panel_regression",
    title="Panel Data Regression Analysis",
    description="Fixed and random effects regression for longitudinal/panel data",
    arguments_schema={
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Name of the dependent variable",
            },
            "predictors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of independent variables",
            },
            "panel_id": {
                "type": "string",
                "description": "Entity identifier (e.g., country, firm, individual)",
            },
            "time_id": {
                "type": "string",
                "description": "Time period identifier (e.g., year, quarter, month)",
            },
            "model_type": {
                "type": "string",
                "enum": ["fixed_effects", "random_effects", "compare_both"],
                "default": "compare_both",
                "description": "Type of panel model to estimate",
            },
            "dataset_description": {
                "type": "string",
                "description": "Description of your panel dataset and research question",
            },
        },
        "required": [
            "target",
            "predictors",
            "panel_id",
            "time_id",
            "dataset_description",
        ],
    },
)
def panel_regression_prompt():
    return """I'll analyze your panel data to understand how {predictors} affect {target} across entities and time.
**Research Context**: {dataset_description}
**Panel Structure**: {panel_id} (entities) × {time_id} (time periods)
**Model Strategy**: {model_type}
**Panel Data Analysis Workflow**
**Step 1: Data Structure Assessment**
- **Panel Balance**: Check for missing observations across entities/time
- **Descriptive Statistics**: Within and between entity variation
- **Data Quality**: Identify gaps, outliers, and data issues
**Step 2: Model Specification**
- **Research Question**: How do {predictors} affect {target}?
- **Panel Structure**: {panel_id} entities observed over {time_id} periods
- **Variable Variation**: Decompose into within and between entity effects
**Step 3: Model Estimation**
Based on your {model_type} preference, I'll estimate appropriate panel models:
- **Fixed Effects Model**: Controls for time-invariant entity characteristics
- **Random Effects Model**: Assumes entity effects uncorrelated with predictors
- **Model Selection**: Use Hausman test to choose optimal specification
**Step 4: Results & Diagnostics**
- **Coefficient Interpretation**: Within-entity vs. between-entity effects
- **Model Fit**: R-squared (within, between, overall)
- **Standard Errors**: Robust to heteroscedasticity and clustering
- **Entity/Time Effects**: Significance and interpretation
**Step 5: Model Validation**
- **Assumption Checking**: Serial correlation, heteroscedasticity tests
- **Robustness Checks**: Alternative specifications and sensitivity analysis
- **Practical Significance**: Economic/substantive interpretation of effects
**Panel Data Requirements**
Your dataset should include:
- **{target}**: Dependent variable
- **{predictors}**: Independent variables
- **{panel_id}**: Entity identifier (must be consistent across time)
- **{time_id}**: Time period identifier
**Ready to Analyze**
Please provide your panel dataset. I'll guide you through the technical analysis and provide clear interpretation of how {predictors} influence {target} in your specific context."""
