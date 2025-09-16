"""
Prompts registry for MCP server.

Implements mature MCP patterns:
- Templated workflows that teach LLMs tool chaining
- Parameterized prompts with typed arguments
- Statistical analysis playbooks

Following the principle: "Ship prompts as workflows."
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
import logging

from ..core.context import Context
from ..core.schemas import validate_schema, SchemaError

logger = logging.getLogger(__name__)


@dataclass
class PromptDefinition:
    """Prompt template metadata and content."""
    
    name: str
    title: str
    description: str
    arguments_schema: Optional[Dict[str, Any]]
    template: str
    annotations: Optional[Dict[str, Any]] = None


class PromptsRegistry:
    """Registry for MCP prompts with templating support."""
    
    def __init__(self):
        self._prompts: Dict[str, PromptDefinition] = {}
    
    def register(
        self,
        name: str,
        title: str,
        description: str,
        template: str,
        arguments_schema: Optional[Dict[str, Any]] = None,
        annotations: Optional[Dict[str, Any]] = None,
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
    
    async def list_prompts(self, context: Context) -> Dict[str, Any]:
        """List available prompts for MCP prompts/list."""
        
        prompts = []
        for prompt_def in self._prompts.values():
            prompt_info = {
                "name": prompt_def.name,
                "title": prompt_def.title,
                "description": prompt_def.description,
            }
            
            if prompt_def.arguments_schema:
                prompt_info["argumentsSchema"] = prompt_def.arguments_schema
            
            if prompt_def.annotations:
                prompt_info["annotations"] = prompt_def.annotations
            
            prompts.append(prompt_info)
        
        await context.info(f"Listed {len(prompts)} available prompts")
        
        return {"prompts": prompts}
    
    async def get_prompt(
        self, 
        context: Context, 
        name: str, 
        arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get a rendered prompt for MCP prompts/get."""
        
        if name not in self._prompts:
            raise ValueError(f"Unknown prompt: {name}")
        
        prompt_def = self._prompts[name]
        arguments = arguments or {}
        
        try:
            # Validate arguments if schema provided
            if prompt_def.arguments_schema:
                validate_schema(
                    arguments, 
                    prompt_def.arguments_schema, 
                    f"prompt '{name}' arguments"
                )
            
            # Render template
            rendered_content = self._render_template(prompt_def.template, arguments)
            
            await context.info(f"Rendered prompt: {name}", arguments=arguments)
            
            return {
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text", 
                            "text": rendered_content
                        }
                    }
                ]
            }
        
        except SchemaError as e:
            await context.error(f"Schema validation failed for prompt '{name}': {e}")
            raise
        
        except Exception as e:
            await context.error(f"Failed to render prompt '{name}': {e}")
            raise
    
    def _render_template(self, template: str, arguments: Dict[str, Any]) -> str:
        """Render template with arguments using simple string formatting."""
        
        try:
            # Use simple string formatting for now
            # Could be enhanced with Jinja2 or similar
            return template.format(**arguments)
        except KeyError as e:
            raise ValueError(f"Missing template argument: {e}")
        except Exception as e:
            raise ValueError(f"Template rendering error: {e}")


def prompt(
    name: str,
    title: str,
    description: str,
    arguments_schema: Optional[Dict[str, Any]] = None,
    annotations: Optional[Dict[str, Any]] = None,
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
    
    def decorator(func: Callable[[], str]):
        
        # Extract template content from function
        template_content = func()
        
        # Store prompt metadata on function
        func._mcp_prompt_name = name
        func._mcp_prompt_title = title
        func._mcp_prompt_description = description
        func._mcp_prompt_template = template_content
        func._mcp_prompt_arguments_schema = arguments_schema
        func._mcp_prompt_annotations = annotations
        
        return func
    
    return decorator


def register_prompt_functions(registry: PromptsRegistry, *functions) -> None:
    """Register multiple functions decorated with @prompt."""
    
    for func in functions:
        if hasattr(func, '_mcp_prompt_name'):
            registry.register(
                name=func._mcp_prompt_name,
                title=func._mcp_prompt_title,
                description=func._mcp_prompt_description,
                template=func._mcp_prompt_template,
                arguments_schema=func._mcp_prompt_arguments_schema,
                annotations=func._mcp_prompt_annotations,
            )
        else:
            logger.warning(f"Function {func.__name__} not decorated with @prompt, skipping")


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
        "required": ["dataset_name", "analysis_goals"]
    }
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
            "model_type": {"type": "string", "enum": ["linear", "logistic", "time_series", "ml"]},
            "focus_areas": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["model_type"]
    }
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