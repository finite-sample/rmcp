#!/usr/bin/env python3
"""
Schema Validation Utilities for RMCP

Provides utilities for validating R script output against declared schemas,
detecting schema drift, and analyzing schema consistency across tools.

These utilities help maintain schema-R output consistency and provide
detailed diagnostics for schema validation failures.

Main Components:
    SchemaDriftDetector: Detects when R scripts evolve but schemas don't
    SchemaConsistencyChecker: Analyzes consistency across tool schemas
    validate_tool_output_with_diagnostics: Comprehensive validation with diagnostics
    generate_schema_validation_report: Creates human-readable validation reports

Usage Examples:
    # Detect schema drift for a single tool
    >>> detector = SchemaDriftDetector()
    >>> analysis = detector.analyze_output(tool_name, r_output, schema)
    >>> if not analysis["is_compliant"]:
    ...     print("Schema drift detected!")

    # Check consistency across all tools
    >>> checker = SchemaConsistencyChecker()
    >>> for name, schema in all_schemas.items():
    ...     checker.add_tool_schema(name, schema)
    >>> consistency = checker.analyze_consistency()

    # Validate with detailed diagnostics
    >>> report = validate_tool_output_with_diagnostics(
    ...     "linear_model", actual_output, declared_schema
    ... )
    >>> print(report["summary"])
"""

from typing import Any

from jsonschema import ValidationError, validate

from ..logging_config import configure_structured_logging, get_logger

logger = get_logger(__name__)


class SchemaDriftDetector:
    """
    Detects drift between R script output and declared schemas.

    Analyzes actual R script output against declared Python schemas to identify
    when R scripts evolve but schemas don't get updated, preventing runtime
    validation errors.

    Attributes:
        violations: List of critical schema violations found during analysis
        warnings: List of potential drift indicators and warnings

    Example:
        >>> detector = SchemaDriftDetector()
        >>> analysis = detector.analyze_output(
        ...     "linear_model",
        ...     actual_r_output,
        ...     declared_schema
        ... )
        >>> if not analysis["is_compliant"]:
        ...     for rec in analysis["recommendations"]:
        ...         print(f"💡 {rec}")
    """

    def __init__(self):
        self.violations: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    def analyze_output(
        self,
        tool_name: str,
        actual_output: dict[str, Any],
        declared_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Analyze actual R output against declared schema and detect drift.

        Args:
            tool_name: Name of the tool being analyzed
            actual_output: Actual output from R script
            declared_schema: Tool's declared output schema

        Returns:
            Analysis report dictionary containing:
            - tool_name (str): Name of analyzed tool
            - violations (List[Dict]): Critical schema violations
            - warnings (List[Dict]): Potential drift indicators
            - recommendations (List[str]): Actionable fix suggestions
            - is_compliant (bool): Whether output matches schema
            - extra_fields (List[str]): Fields in output but not schema
            - missing_fields (List[str]): Required fields missing from output
            - type_mismatches (List[Dict]): Fields with incorrect types
            - strict_validation (str): "PASSED" or "FAILED"

        Example:
            >>> detector = SchemaDriftDetector()
            >>> analysis = detector.analyze_output(
            ...     "linear_model",
            ...     {"r_squared": 0.85, "new_field": 123},
            ...     {"properties": {"r_squared": {"type": "number"}}}
            ... )
            >>> print(analysis["extra_fields"])
            ['new_field']
            >>> for rec in analysis["recommendations"]:
            ...     print(f"💡 {rec}")
        """
        analysis: dict[str, Any] = {
            "tool_name": tool_name,
            "violations": [],
            "warnings": [],
            "recommendations": [],
            "is_compliant": True,
            "extra_fields": [],
            "missing_fields": [],
            "type_mismatches": [],
        }

        try:
            # First, try strict validation
            validate(instance=actual_output, schema=declared_schema)
            analysis["strict_validation"] = "PASSED"
        except ValidationError as e:
            analysis["strict_validation"] = "FAILED"
            analysis["is_compliant"] = False
            analysis["violations"].append(
                {
                    "type": "validation_error",
                    "message": e.message,
                    "path": list(e.absolute_path),
                    "value": e.instance,
                }
            )

        # Detailed field analysis
        if declared_schema.get("type") == "object" and "properties" in declared_schema:
            self._analyze_object_schema(actual_output, declared_schema, analysis)

        # Generate recommendations
        self._generate_recommendations(analysis)

        return analysis

    def _analyze_object_schema(
        self,
        actual_output: dict[str, Any],
        declared_schema: dict[str, Any],
        analysis: dict[str, Any],
    ) -> None:
        """
        Analyze object schema for field and type drift.

        Performs detailed comparison between actual R output and declared schema,
        identifying missing required fields, unexpected extra fields, and type
        mismatches that indicate schema drift.

        Args:
            actual_output: Dictionary containing actual R script output
            declared_schema: JSON Schema object definition with properties
            analysis: Analysis dictionary to populate with findings

        Side Effects:
            Modifies analysis dict by adding to:
            - violations: Critical schema violations
            - warnings: Potential drift indicators
            - missing_fields: Required fields not in output
            - extra_fields: Output fields not in schema
            - type_mismatches: Fields with wrong data types
        """
        properties = declared_schema["properties"]
        required_fields = declared_schema.get("required", [])
        allows_additional = declared_schema.get("additionalProperties", True)

        # Check for missing required fields
        missing_required = [f for f in required_fields if f not in actual_output]
        if missing_required:
            analysis["missing_fields"].extend(missing_required)
            analysis["violations"].append(
                {"type": "missing_required_fields", "fields": missing_required}
            )

        # Check for extra fields (potential schema drift)
        extra_fields = [f for f in actual_output.keys() if f not in properties]
        if extra_fields:
            analysis["extra_fields"].extend(extra_fields)
            if not allows_additional:
                analysis["violations"].append(
                    {"type": "extra_fields_not_allowed", "fields": extra_fields}
                )
            else:
                analysis["warnings"].append(
                    {
                        "type": "extra_fields_detected",
                        "fields": extra_fields,
                        "message": "R script produces fields not in schema - potential schema drift",
                    }
                )

        # Check for type mismatches
        for field, value in actual_output.items():
            if field in properties:
                expected_type = properties[field].get("type")
                if expected_type:
                    actual_type = self._get_json_type(value)
                    if not self._types_compatible(actual_type, expected_type):
                        analysis["type_mismatches"].append(
                            {
                                "field": field,
                                "expected_type": expected_type,
                                "actual_type": actual_type,
                                "value": value,
                            }
                        )
                        analysis["violations"].append(
                            {
                                "type": "type_mismatch",
                                "field": field,
                                "expected": expected_type,
                                "actual": actual_type,
                            }
                        )

    def _get_json_type(self, value: Any) -> str:
        """
        Convert Python type to JSON Schema type.

        Maps Python runtime types to their corresponding JSON Schema type names
        for accurate schema validation and drift detection.

        Args:
            value: Python value of any type

        Returns:
            JSON Schema type string ("string", "number", "integer", "boolean",
            "array", "object", "null", or "unknown" for unmapped types)

        Example:
            >>> detector._get_json_type(42)
            'integer'
            >>> detector._get_json_type([1, 2, 3])
            'array'
        """
        type_mapping = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
            type(None): "null",
        }
        return type_mapping.get(type(value), "unknown")

    def _types_compatible(self, actual_type: str, expected_type: str) -> bool:
        """
        Check if actual type is compatible with expected type.

        Handles JSON Schema type compatibility rules, including number/integer
        interoperability and union types. More permissive than strict equality
        to account for valid type coercions.

        Args:
            actual_type: JSON Schema type from actual output
            expected_type: JSON Schema type from declared schema

        Returns:
            True if types are compatible, False otherwise

        Examples:
            >>> detector._types_compatible("integer", "number")
            True  # integers are valid numbers
            >>> detector._types_compatible("string", "number")
            False  # incompatible types
        """
        # Handle number/integer compatibility
        if expected_type == "number" and actual_type in ["integer", "number"]:
            return True
        if expected_type == "integer" and actual_type == "integer":
            return True

        # Handle union types
        if isinstance(expected_type, list):
            return actual_type in expected_type

        return actual_type == expected_type

    def _generate_recommendations(self, analysis: dict[str, Any]) -> None:
        """
        Generate actionable recommendations based on analysis.

        Creates human-readable recommendations for fixing schema drift issues
        based on the violations and warnings found during analysis.

        Args:
            analysis: Analysis dictionary containing drift findings

        Side Effects:
            Adds 'recommendations' list to analysis dict with actionable
            suggestions for resolving schema mismatches

        Note:
            Recommendations are prioritized by severity: missing required fields,
            extra fields, type mismatches, then general compliance status.
        """
        recommendations = []

        if analysis["missing_fields"]:
            recommendations.append(
                f"R script should output these missing required fields: {analysis['missing_fields']}"
            )

        if analysis["extra_fields"]:
            recommendations.append(
                f"Consider adding these fields to schema or removing from R script: {analysis['extra_fields']}"
            )

        if analysis["type_mismatches"]:
            for mismatch in analysis["type_mismatches"]:
                recommendations.append(
                    f"Fix type for field '{mismatch['field']}': "
                    f"R outputs {mismatch['actual_type']}, schema expects {mismatch['expected_type']}"
                )

        if not recommendations and analysis["is_compliant"]:
            recommendations.append(
                "Schema and R output are fully compliant - no action needed"
            )

        analysis["recommendations"] = recommendations


class SchemaConsistencyChecker:
    """
    Checks schema consistency across multiple tools.

    Analyzes schema definitions across the entire tool ecosystem to identify
    inconsistencies in field naming, type usage, and structural patterns
    that could confuse users or indicate design issues.

    Attributes:
        tool_schemas: Dictionary mapping tool names to their schema definitions
        common_patterns: Analysis of field usage patterns across tools

    Example:
        >>> checker = SchemaConsistencyChecker()
        >>> for tool_name, schema in all_tool_schemas.items():
        ...     checker.add_tool_schema(tool_name, schema)
        >>> analysis = checker.analyze_consistency()
        >>> if analysis["type_inconsistencies"]:
        ...     print("Found type inconsistencies across tools")
    """

    def __init__(self):
        self.tool_schemas: dict[str, dict[str, Any]] = {}
        self.common_patterns: dict[str, list[str]] = {}

    def add_tool_schema(self, tool_name: str, schema: dict[str, Any]) -> None:
        """Add a tool's schema for consistency analysis."""
        self.tool_schemas[tool_name] = schema

    def analyze_consistency(self) -> dict[str, Any]:
        """
        Analyze schemas for consistency patterns and violations.

        Returns:
            Consistency analysis dictionary containing:
            - total_tools (int): Number of tools analyzed
            - common_field_patterns (Dict): Field usage patterns across tools
            - type_inconsistencies (List[Dict]): Fields with inconsistent types
            - naming_inconsistencies (List[Dict]): Similar field names
            - recommendations (List[str]): Suggestions for standardization

        Example:
            >>> checker = SchemaConsistencyChecker()
            >>> checker.add_tool_schema("tool1", schema1)
            >>> checker.add_tool_schema("tool2", schema2)
            >>> analysis = checker.analyze_consistency()
            >>> if analysis["type_inconsistencies"]:
            ...     print("Found inconsistent field types:")
            ...     for issue in analysis["type_inconsistencies"]:
            ...         print(f"  {issue['field']}: {issue['type_variations']}")
        """
        analysis: dict[str, Any] = {
            "total_tools": len(self.tool_schemas),
            "common_field_patterns": {},
            "type_inconsistencies": [],
            "naming_inconsistencies": [],
            "recommendations": [],
        }

        # Analyze common field patterns
        field_types: dict[str, dict[str, list[str]]] = {}
        field_descriptions: dict[str, dict[str, list[str]]] = {}

        for tool_name, schema in self.tool_schemas.items():
            if schema.get("type") == "object" and "properties" in schema:
                for field, field_schema in schema["properties"].items():
                    field_type = field_schema.get("type", "unknown")
                    field_desc = field_schema.get("description", "")

                    if field not in field_types:
                        field_types[field] = {}
                    if field_type not in field_types[field]:
                        field_types[field][field_type] = []
                    field_types[field][field_type].append(tool_name)

                    if field not in field_descriptions:
                        field_descriptions[field] = {}
                    if field_desc not in field_descriptions[field]:
                        field_descriptions[field][field_desc] = []
                    field_descriptions[field][field_desc].append(tool_name)

        # Detect type inconsistencies
        for field, type_usage in field_types.items():
            if len(type_usage) > 1:
                analysis["type_inconsistencies"].append(
                    {"field": field, "type_variations": type_usage}
                )

        # Detect naming inconsistencies (similar fields with different names)
        self._detect_naming_inconsistencies(field_types, analysis)

        # Generate recommendations
        self._generate_consistency_recommendations(analysis)

        return analysis

    def _detect_naming_inconsistencies(
        self, field_types: dict[str, dict[str, list[str]]], analysis: dict[str, Any]
    ) -> None:
        """
        Detect potential naming inconsistencies across tool schemas.

        Uses edit distance similarity to identify field names that might
        represent the same concept but use different naming conventions.

        Args:
            field_types: Mapping of field names to their type usage across tools
            analysis: Analysis dictionary to populate with findings

        Side Effects:
            Adds 'naming_inconsistencies' list to analysis with similar field
            pairs that might benefit from standardization

        Note:
            Uses 0.7 similarity threshold to balance false positives with
            meaningful suggestions (e.g., "p_value" vs "pvalue")
        """
        # Group similar field names (simple similarity check)
        field_names = list(field_types.keys())
        similar_groups = []

        for i, field1 in enumerate(field_names):
            for field2 in field_names[i + 1 :]:
                similarity = self._calculate_field_similarity(field1, field2)
                if similarity > 0.7:  # Threshold for similarity
                    similar_groups.append(
                        {
                            "field1": field1,
                            "field2": field2,
                            "similarity": similarity,
                            "tools1": list(set().union(*field_types[field1].values())),
                            "tools2": list(set().union(*field_types[field2].values())),
                        }
                    )

        analysis["naming_inconsistencies"] = similar_groups

    def _calculate_field_similarity(self, field1: str, field2: str) -> float:
        """
        Calculate similarity between two field names using edit distance.

        Computes normalized edit distance (Levenshtein distance) to measure
        how similar two field names are, useful for detecting potential
        naming inconsistencies across schemas.

        Args:
            field1: First field name to compare
            field2: Second field name to compare

        Returns:
            Similarity score from 0.0 (completely different) to 1.0 (identical)

        Example:
            >>> checker._calculate_field_similarity("p_value", "pvalue")
            0.875  # High similarity
            >>> checker._calculate_field_similarity("name", "coefficient")
            0.1    # Low similarity
        """

        # Simple edit distance based similarity
        def edit_distance(s1, s2):
            """
            Calculate Levenshtein edit distance between two strings.

            Args:
                s1: First string
                s2: Second string

            Returns:
                Minimum number of single-character edits needed to transform s1 into s2
            """
            if len(s1) < len(s2):
                return edit_distance(s2, s1)
            if len(s2) == 0:
                return len(s1)

            previous_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row

            return previous_row[-1]

        max_len = max(len(field1), len(field2))
        if max_len == 0:
            return 1.0

        distance = edit_distance(field1.lower(), field2.lower())
        return 1 - (distance / max_len)

    def _generate_consistency_recommendations(self, analysis: dict[str, Any]) -> None:
        """
        Generate recommendations for improving schema consistency.

        Creates actionable suggestions for standardizing schemas across tools
        based on detected type inconsistencies and naming variations.

        Args:
            analysis: Analysis dictionary containing consistency findings

        Side Effects:
            Adds 'recommendations' list to analysis with suggestions for
            improving schema standardization across the tool ecosystem

        Note:
            Limits recommendations to top 3 issues per category to avoid
            overwhelming output while highlighting the most impactful changes.
        """
        recommendations = []

        if analysis["type_inconsistencies"]:
            recommendations.append(
                "Consider standardizing field types across tools for consistency"
            )
            for inconsistency in analysis["type_inconsistencies"][:3]:  # Show top 3
                field = inconsistency["field"]
                variations = inconsistency["type_variations"]
                recommendations.append(
                    f"Field '{field}' has inconsistent types: {list(variations.keys())}"
                )

        if analysis["naming_inconsistencies"]:
            recommendations.append(
                "Consider standardizing field names to reduce confusion"
            )
            for inconsistency in analysis["naming_inconsistencies"][:3]:  # Show top 3
                recommendations.append(
                    f"Similar fields '{inconsistency['field1']}' and '{inconsistency['field2']}' "
                    f"might benefit from consistent naming"
                )

        if not recommendations:
            recommendations.append("Schema consistency looks good across all tools")

        analysis["recommendations"] = recommendations


def validate_tool_output_with_diagnostics(
    tool_name: str,
    actual_output: dict[str, Any],
    declared_schema: dict[str, Any],
    include_drift_analysis: bool = True,
) -> dict[str, Any]:
    """
    Comprehensive validation with detailed diagnostics.

    Args:
        tool_name: Name of the tool being validated
        actual_output: Actual output from tool execution
        declared_schema: Tool's declared output schema
        include_drift_analysis: Whether to include schema drift analysis

    Returns:
        Validation report dictionary containing:
        - tool_name (str): Name of validated tool
        - validation_passed (bool): Whether validation succeeded
        - validation_errors (List[Dict]): Detailed error information
        - drift_analysis (Dict): Schema drift analysis (if enabled)
        - summary (str): Human-readable validation summary

        Each validation error contains:
        - message (str): Error description
        - path (List): JSON path to problematic field
        - value (str): Actual value (truncated if long)
        - schema_path (List): JSON Schema path that failed

    Example:
        >>> report = validate_tool_output_with_diagnostics(
        ...     "correlation_analysis",
        ...     r_script_output,
        ...     correlation_analysis._mcp_tool_output_schema
        ... )
        >>> if not report["validation_passed"]:
        ...     print(report["summary"])
        ...     for error in report["validation_errors"]:
        ...         print(f"  ❌ {error['message']}")
        >>> if report["drift_analysis"] and report["drift_analysis"]["extra_fields"]:
        ...     print(f"New fields detected: {report['drift_analysis']['extra_fields']}")
    """
    report: dict[str, Any] = {
        "tool_name": tool_name,
        "validation_passed": False,
        "validation_errors": [],
        "drift_analysis": None,
        "summary": "",
    }

    try:
        # Remove formatting info before validation (as done in production)
        cleaned_output = {k: v for k, v in actual_output.items() if k != "_formatting"}

        # Strict validation
        validate(instance=cleaned_output, schema=declared_schema)
        report["validation_passed"] = True
        report["summary"] = f"✅ Tool '{tool_name}' output matches declared schema"

    except ValidationError as e:
        report["validation_errors"].append(
            {
                "message": e.message,
                "path": list(e.absolute_path),
                "value": (
                    str(e.instance)[:200] + "..."
                    if len(str(e.instance)) > 200
                    else str(e.instance)
                ),
                "schema_path": list(e.schema_path),
            }
        )
        report["summary"] = f"❌ Tool '{tool_name}' output validation failed"

    except Exception as e:
        report["validation_errors"].append(
            {
                "message": f"Unexpected validation error: {str(e)}",
                "path": [],
                "value": "",
                "schema_path": [],
            }
        )
        report["summary"] = (
            f"⚠️ Tool '{tool_name}' validation encountered unexpected error"
        )

    # Drift analysis
    if include_drift_analysis:
        detector = SchemaDriftDetector()
        cleaned_output = {k: v for k, v in actual_output.items() if k != "_formatting"}
        report["drift_analysis"] = detector.analyze_output(
            tool_name, cleaned_output, declared_schema
        )

    return report


def generate_schema_validation_report(validation_results: list[dict[str, Any]]) -> str:
    """
    Generate a human-readable schema validation report.

    Creates a comprehensive markdown-formatted report summarizing schema
    validation results across multiple tools, including failure analysis
    and actionable recommendations.

    Args:
        validation_results: List of validation result dictionaries from
                          validate_tool_output_with_diagnostics()

    Returns:
        Multi-line markdown string containing:
        - Summary statistics (passed/failed counts)
        - Common issues grouped by error type
        - Detailed failure analysis for failed tools
        - Prioritized recommendations for fixes

    Example:
        >>> results = [validate_tool_output_with_diagnostics(...)]
        >>> report = generate_schema_validation_report(results)
        >>> print(report)
        # RMCP Schema Validation Report
        📊 **Summary**: 8/10 tools passed validation
        ...
    """

    total_tools = len(validation_results)
    passed_tools = sum(
        1 for result in validation_results if result["validation_passed"]
    )
    failed_tools = total_tools - passed_tools

    report = []
    report.append("# RMCP Schema Validation Report")
    report.append("=" * 50)
    report.append(
        f"📊 **Summary**: {passed_tools}/{total_tools} tools passed validation"
    )
    report.append("")

    if failed_tools == 0:
        report.append("🎉 **All tools passed schema validation!**")
        report.append("")
        report.append("Your R scripts are producing output that perfectly matches")
        report.append("the declared schemas. No action needed.")
    else:
        report.append(f"⚠️ **{failed_tools} tools failed validation**")
        report.append("")

        # Group failures by type
        common_issues: dict[str, list[str]] = {}
        for result in validation_results:
            if not result["validation_passed"]:
                for error in result["validation_errors"]:
                    issue_type = (
                        error["message"].split(":")[0]
                        if ":" in error["message"]
                        else error["message"]
                    )
                    if issue_type not in common_issues:
                        common_issues[issue_type] = []
                    common_issues[issue_type].append(result["tool_name"])

        report.append("## Common Issues")
        for issue_type, affected_tools in common_issues.items():
            report.append(f"- **{issue_type}**: {len(affected_tools)} tools affected")
            report.append(f"  - Tools: {', '.join(affected_tools[:5])}")
            if len(affected_tools) > 5:
                report.append(f"    ... and {len(affected_tools) - 5} more")
            report.append("")

    # Detailed results for failed tools
    failed_results = [r for r in validation_results if not r["validation_passed"]]
    if failed_results:
        report.append("## Detailed Failure Analysis")
        for result in failed_results[:10]:  # Show first 10 failures
            report.append(f"### {result['tool_name']}")
            for error in result["validation_errors"][
                :3
            ]:  # Show first 3 errors per tool
                report.append(f"- **Error**: {error['message']}")
                if error["path"]:
                    report.append(
                        f"  - **Path**: {' -> '.join(map(str, error['path']))}"
                    )
                report.append("")

    # Recommendations
    report.append("## Recommendations")
    if failed_tools > 0:
        report.append(
            "1. **Fix R script output**: Update R scripts to match declared schemas"
        )
        report.append(
            "2. **Update schemas**: If R output is correct, update Python schemas"
        )
        report.append(
            "3. **Test locally**: Use `pytest tests/integration/test_schema_validation.py`"
        )
    else:
        report.append("1. **Keep monitoring**: Run schema validation tests regularly")
        report.append(
            "2. **Document changes**: Update schemas when modifying R scripts"
        )

    return "\n".join(report)


# CLI utility for running schema validation
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RMCP Schema Validation Utility")
    parser.add_argument("--tool", help="Validate specific tool only")
    parser.add_argument(
        "--report", action="store_true", help="Generate detailed report"
    )
    parser.add_argument("--drift", action="store_true", help="Include drift analysis")

    args = parser.parse_args()

    # Configure structured logging for utility
    configure_structured_logging(
        level="INFO", development_mode=True, enable_console=True
    )

    logger.info("RMCP Schema Validation Utility")
    logger.info(
        "This utility requires manual implementation of tool execution for validation"
    )
    logger.info(
        "Use pytest tests/integration/test_schema_validation.py for automated testing"
    )
