#!/usr/bin/env python3
"""
Schema Validation Utilities for RMCP

Provides utilities for validating R script output against declared schemas,
detecting schema drift, and analyzing schema consistency across tools.

These utilities help maintain schema-R output consistency and provide
detailed diagnostics for schema validation failures.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from jsonschema import ValidationError, validate

logger = logging.getLogger(__name__)


class SchemaDriftDetector:
    """Detects drift between R script output and declared schemas."""

    def __init__(self):
        self.violations: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []

    def analyze_output(
        self,
        tool_name: str,
        actual_output: Dict[str, Any],
        declared_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Analyze actual R output against declared schema and detect drift.

        Args:
            tool_name: Name of the tool being analyzed
            actual_output: Actual output from R script
            declared_schema: Tool's declared output schema

        Returns:
            Analysis report with violations, warnings, and recommendations
        """
        analysis = {
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
        actual_output: Dict[str, Any],
        declared_schema: Dict[str, Any],
        analysis: Dict[str, Any],
    ) -> None:
        """Analyze object schema for field and type drift."""
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
        """Convert Python type to JSON Schema type."""
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
        """Check if actual type is compatible with expected type."""
        # Handle number/integer compatibility
        if expected_type == "number" and actual_type in ["integer", "number"]:
            return True
        if expected_type == "integer" and actual_type == "integer":
            return True

        # Handle union types
        if isinstance(expected_type, list):
            return actual_type in expected_type

        return actual_type == expected_type

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> None:
        """Generate actionable recommendations based on analysis."""
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
    """Checks schema consistency across multiple tools."""

    def __init__(self):
        self.tool_schemas: Dict[str, Dict[str, Any]] = {}
        self.common_patterns: Dict[str, List[str]] = {}

    def add_tool_schema(self, tool_name: str, schema: Dict[str, Any]) -> None:
        """Add a tool's schema for consistency analysis."""
        self.tool_schemas[tool_name] = schema

    def analyze_consistency(self) -> Dict[str, Any]:
        """Analyze schemas for consistency patterns and violations."""
        analysis = {
            "total_tools": len(self.tool_schemas),
            "common_field_patterns": {},
            "type_inconsistencies": [],
            "naming_inconsistencies": [],
            "recommendations": [],
        }

        # Analyze common field patterns
        field_types = {}
        field_descriptions = {}

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
        self, field_types: Dict[str, Dict[str, List[str]]], analysis: Dict[str, Any]
    ) -> None:
        """Detect potential naming inconsistencies."""
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
        """Calculate similarity between two field names."""

        # Simple edit distance based similarity
        def edit_distance(s1, s2):
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

    def _generate_consistency_recommendations(self, analysis: Dict[str, Any]) -> None:
        """Generate recommendations for improving schema consistency."""
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
    actual_output: Dict[str, Any],
    declared_schema: Dict[str, Any],
    include_drift_analysis: bool = True,
) -> Dict[str, Any]:
    """
    Comprehensive validation with detailed diagnostics.

    Args:
        tool_name: Name of the tool being validated
        actual_output: Actual output from tool execution
        declared_schema: Tool's declared output schema
        include_drift_analysis: Whether to include schema drift analysis

    Returns:
        Comprehensive validation report
    """
    report = {
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


def generate_schema_validation_report(validation_results: List[Dict[str, Any]]) -> str:
    """Generate a human-readable schema validation report."""

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
        common_issues = {}
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
    import sys
    from pathlib import Path

    # Add rmcp to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    parser = argparse.ArgumentParser(description="RMCP Schema Validation Utility")
    parser.add_argument("--tool", help="Validate specific tool only")
    parser.add_argument(
        "--report", action="store_true", help="Generate detailed report"
    )
    parser.add_argument("--drift", action="store_true", help="Include drift analysis")

    args = parser.parse_args()

    print("RMCP Schema Validation Utility")
    print(
        "This utility requires manual implementation of tool execution for validation"
    )
    print(
        "Use pytest tests/integration/test_schema_validation.py for automated testing"
    )
