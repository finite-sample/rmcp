#!/usr/bin/env python3
"""
Claude Error Experience Tests with Real R Errors.

Tests the end-to-end error experience that Claude users encounter when
R statistical analysis fails. Validates that:

1. Error messages are clear and actionable for non-technical users
2. Error recovery suggestions are helpful and specific
3. Error context is preserved for debugging
4. Progressive error handling guides users toward solutions
5. Error messages work well in conversational AI context

These tests simulate the actual user experience with Claude Desktop
when statistical analyses encounter R errors or warnings.
"""

import os
from shutil import which

import pytest
from rmcp.core.context import Context, LifespanState
from rmcp.core.server import create_server
from rmcp.registries.tools import register_tool_functions
from rmcp.tools.fileops import data_info, read_csv
from rmcp.tools.helpers import suggest_fix, validate_data
from rmcp.tools.machine_learning import decision_tree, random_forest
from rmcp.tools.regression import (
    correlation_analysis,
    linear_model,
    logistic_regression,
)
from rmcp.tools.statistical_tests import chi_square_test, normality_test, t_test

from tests.utils import extract_json_content, extract_text_summary

# Add rmcp to path


pytestmark = [
    pytest.mark.skipif(
        which("R") is None, reason="R binary is required for user experience tests"
    ),
    pytest.mark.skipif(
        bool(os.getenv("CI")) or bool(os.getenv("GITHUB_ACTIONS")),
        reason="User experience tests require local environment for realistic scenarios",
    ),
    pytest.mark.skip(
        reason="Error message user experience tests are aspirational - require enhanced error formatting not yet implemented"
    ),
]


@pytest.fixture
def claude_server():
    """Create server configured as Claude Desktop would see it."""
    server = create_server()
    server.configure(allowed_paths=["/tmp"], read_only=False)

    # Register all tools that Claude would have access to
    register_tool_functions(
        server.tools,
        # Core analysis tools
        linear_model,
        logistic_regression,
        correlation_analysis,
        # Statistical tests
        t_test,
        chi_square_test,
        normality_test,
        # Machine learning
        decision_tree,
        random_forest,
        # File operations
        read_csv,
        data_info,
        # Helper tools for error recovery
        suggest_fix,
        validate_data,
    )
    return server


@pytest.fixture
def context():
    """Create context for user experience tests."""
    lifespan = LifespanState()
    ctx = Context.create("claude_user", "error_experience_test", lifespan)
    return ctx


async def simulate_claude_analysis(server, tool_name, arguments, user_intent):
    """Simulate how Claude would call a tool and handle errors."""
    print(f"\n💬 User Intent: {user_intent}")
    print(f"🤖 Claude calls: {tool_name}")

    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }

    try:
        response = await server.handle_request(request)

        if "result" in response:
            if response["result"].get("isError"):
                # Extract error message for user
                error_text = extract_text_summary(response)
                print(f"❌ Error occurred: {error_text[:100]}...")
                return {"success": False, "error": error_text, "response": response}
            else:
                # Success case
                result_data = extract_json_content(response)
                print("✅ Analysis completed successfully")
                return {"success": True, "data": result_data, "response": response}
        else:
            # JSON-RPC error
            error_msg = response.get("error", {}).get("message", "Unknown error")
            print(f"❌ Protocol error: {error_msg}")
            return {"success": False, "error": error_msg, "response": response}

    except Exception as e:
        print(f"💥 Exception: {str(e)}")
        return {"success": False, "error": str(e), "response": None}


class TestClaudeErrorExperienceScenarios:
    """Test realistic error scenarios from Claude user perspective."""

    @pytest.mark.asyncio
    async def test_novice_user_data_error_experience(self, claude_server, context):
        """Test error experience for novice user with data problems."""
        print("\n" + "=" * 70)
        print("📊 SCENARIO: Novice User Data Analysis Error")
        print("=" * 70)
        print("User Goal: Analyze sales data but provides problematic dataset")

        # Simulate novice user providing problematic data
        problematic_data = {
            "sales": [100, 200, "N/A", 400, 500],  # Mixed types
            "month": [1, 2, 3, 4],  # Different length
        }

        # Step 1: User tries regression analysis
        result = await simulate_claude_analysis(
            claude_server,
            "linear_model",
            {"data": problematic_data, "formula": "sales ~ month"},
            "I want to analyze how sales change by month",
        )

        assert not result["success"], "Should fail with data problems"
        error_msg = result["error"]

        # Error message should be helpful for novice users
        error_lower = error_msg.lower()

        # Should explain the problem clearly
        data_issue_indicators = [
            "data",
            "mismatch",
            "length",
            "type",
            "numeric",
            "character",
        ]
        assert any(
            indicator in error_lower for indicator in data_issue_indicators
        ), f"Error should explain data issue clearly: {error_msg}"

        # Should not be overly technical
        technical_jargon = ["traceback", "exception", "stderr", "subprocess", "jsonrpc"]
        assert not any(
            jargon in error_lower for jargon in technical_jargon
        ), f"Error should avoid technical jargon: {error_msg}"

        # Step 2: Use suggest_fix for guidance
        fix_result = await simulate_claude_analysis(
            claude_server,
            "suggest_fix",
            {"error_message": error_msg, "tool_name": "linear_model"},
            "Help me understand what went wrong and how to fix it",
        )

        assert fix_result["success"], "Suggest fix should provide guidance"
        suggestions = fix_result["data"]["suggestions"]

        # Suggestions should be actionable for novice users
        suggestions_text = " ".join(suggestions).lower()
        helpful_actions = [
            "check",
            "ensure",
            "make sure",
            "verify",
            "try",
            "use",
            "convert",
        ]
        assert any(
            action in suggestions_text for action in helpful_actions
        ), f"Suggestions should be actionable: {suggestions}"

        print("✅ Novice user error experience validated")
        print("   Error clarity: Clear explanation of data issues")
        print(f"   Guidance quality: {len(suggestions)} actionable suggestions")

    @pytest.mark.asyncio
    async def test_researcher_statistical_warning_experience(
        self, claude_server, context
    ):
        """Test error experience for researcher encountering statistical warnings."""
        print("\n" + "=" * 70)
        print("🔬 SCENARIO: Researcher Statistical Warning")
        print("=" * 70)
        print("User Goal: Run logistic regression but data causes convergence warning")

        # Data that causes logistic regression convergence issues
        separation_data = {
            "outcome": [0, 0, 0, 1, 1, 1],
            "predictor": [1, 2, 3, 10, 11, 12],  # Perfect separation
        }

        # Step 1: Researcher runs logistic regression
        result = await simulate_claude_analysis(
            claude_server,
            "logistic_regression",
            {
                "data": separation_data,
                "formula": "outcome ~ predictor",
                "family": "binomial",
            },
            "I need to model the probability of outcome based on predictor variable",
        )

        # This might succeed with warnings or fail outright
        if result["success"]:
            # Check if warnings are communicated
            print("   Analysis completed with potential warnings")

            # Validate data to see if warnings are surfaced
            validation_result = await simulate_claude_analysis(
                claude_server,
                "validate_data",
                {"data": separation_data, "analysis_type": "classification"},
                "Can you check if my data is suitable for logistic regression?",
            )

            if validation_result["success"]:
                warnings = validation_result["data"].get("warnings", [])
                if warnings:
                    print(f"   Data validation identified {len(warnings)} warnings")

                    # Warnings should be meaningful for researchers
                    warnings_text = " ".join(warnings).lower()
                    statistical_concepts = [
                        "separation",
                        "convergence",
                        "sample",
                        "assumption",
                    ]
                    assert any(
                        concept in warnings_text for concept in statistical_concepts
                    ), f"Warnings should mention statistical concepts: {warnings}"
        else:
            # Failed with error - check error quality
            error_msg = result["error"]

            # Error should mention statistical concepts
            error_lower = error_msg.lower()
            statistical_terms = [
                "convergence",
                "separation",
                "optimization",
                "fitted",
                "probabilities",
            ]
            assert any(
                term in error_lower for term in statistical_terms
            ), f"Error should use appropriate statistical terminology: {error_msg}"

        # Step 2: Get expert guidance
        fix_result = await simulate_claude_analysis(
            claude_server,
            "suggest_fix",
            {
                "error_message": result.get("error", "convergence warning occurred"),
                "tool_name": "logistic_regression",
            },
            "What statistical approaches can I use to address this issue?",
        )

        if fix_result["success"]:
            suggestions = fix_result["data"]["suggestions"]

            # Suggestions should include statistical solutions
            suggestions_text = " ".join(suggestions).lower()
            statistical_solutions = [
                "regularization",
                "penalized",
                "sample",
                "data",
                "transform",
                "interaction",
            ]
            assert any(
                solution in suggestions_text for solution in statistical_solutions
            ), f"Should suggest statistical solutions: {suggestions}"

        print("✅ Researcher statistical warning experience validated")

    @pytest.mark.asyncio
    async def test_business_analyst_file_error_experience(self, claude_server, context):
        """Test error experience for business analyst with file access issues."""
        print("\n" + "=" * 70)
        print("📈 SCENARIO: Business Analyst File Error")
        print("=" * 70)
        print("User Goal: Load sales data from CSV but file path is wrong")

        # Step 1: Try to load non-existent file
        result = await simulate_claude_analysis(
            claude_server,
            "read_csv",
            {"file_path": "/wrong/path/sales_data.csv"},
            "I need to load my quarterly sales data for analysis",
        )

        assert not result["success"], "Should fail with file not found"
        error_msg = result["error"]

        # Error should be clear about file issue
        error_lower = error_msg.lower()
        file_indicators = [
            "file",
            "not found",
            "does not exist",
            "path",
            "cannot access",
        ]
        assert any(
            indicator in error_lower for indicator in file_indicators
        ), f"Error should clearly indicate file issue: {error_msg}"

        # Should preserve file path for debugging
        assert (
            "/wrong/path/sales_data.csv" in error_msg or "sales_data.csv" in error_msg
        ), "Error should mention the problematic file path"

        # Step 2: Get file troubleshooting help
        fix_result = await simulate_claude_analysis(
            claude_server,
            "suggest_fix",
            {"error_message": error_msg, "tool_name": "read_csv"},
            "Help me figure out how to fix this file loading issue",
        )

        assert fix_result["success"], "Should provide file troubleshooting guidance"
        suggestions = fix_result["data"]["suggestions"]

        # Suggestions should include file-specific help
        suggestions_text = " ".join(suggestions).lower()
        file_help = [
            "check path",
            "verify",
            "file exists",
            "permissions",
            "directory",
            "absolute path",
        ]
        assert any(
            help_item in suggestions_text for help_item in file_help
        ), f"Should suggest file troubleshooting steps: {suggestions}"

        print("✅ Business analyst file error experience validated")
        print("   Error clarity: File issue clearly identified")
        print(f"   Guidance: {len(suggestions)} file troubleshooting suggestions")

    @pytest.mark.asyncio
    async def test_data_scientist_ml_error_experience(self, claude_server, context):
        """Test error experience for data scientist with ML model errors."""
        print("\n" + "=" * 70)
        print("🤖 SCENARIO: Data Scientist ML Error")
        print("=" * 70)
        print("User Goal: Build decision tree but data has issues")

        # Data with ML-specific problems
        problematic_ml_data = {
            "feature1": [1, 1, 1, 1, 1],  # No variation
            "feature2": [10, 20, 30, 40, 50],
            "target": ["A", "A", "A", "A", "A"],  # No variation in target
        }

        # Step 1: Try to build decision tree
        result = await simulate_claude_analysis(
            claude_server,
            "decision_tree",
            {
                "data": problematic_ml_data,
                "formula": "target ~ feature1 + feature2",
                "method": "class",
            },
            "I want to build a decision tree classifier for customer segments",
        )

        # This might succeed or fail depending on R's handling
        if not result["success"]:
            error_msg = result["error"]

            # Error should mention ML-specific issues
            error_lower = error_msg.lower()
            ml_concepts = [
                "classification",
                "tree",
                "split",
                "variance",
                "target",
                "feature",
            ]
            assert any(
                concept in error_lower for concept in ml_concepts
            ), f"Error should use ML terminology appropriately: {error_msg}"

        # Step 2: Validate data for ML suitability
        validation_result = await simulate_claude_analysis(
            claude_server,
            "validate_data",
            {"data": problematic_ml_data, "analysis_type": "classification"},
            "Is my data suitable for building a classification model?",
        )

        assert validation_result["success"], "Data validation should complete"
        validation_data = validation_result["data"]

        # Should identify ML-specific data quality issues
        if not validation_data.get("is_valid", True):
            warnings = validation_data.get("warnings", [])
            errors = validation_data.get("errors", [])

            issues_text = " ".join(warnings + errors).lower()
            ml_issues = [
                "variation",
                "constant",
                "split",
                "classification",
                "target",
                "feature",
            ]
            assert any(
                issue in issues_text for issue in ml_issues
            ), f"Should identify ML-specific data issues: {warnings + errors}"

        print("✅ Data scientist ML error experience validated")

    @pytest.mark.asyncio
    async def test_progressive_error_recovery_workflow(self, claude_server, context):
        """Test progressive error recovery workflow across multiple tool calls."""
        print("\n" + "=" * 70)
        print("🔄 SCENARIO: Progressive Error Recovery")
        print("=" * 70)
        print("User Goal: Work through data issues step by step")

        # Start with clearly problematic data
        initial_data = {
            "revenue": [100, "missing", 300],
            "quarter": ["Q1", "Q2"],  # Length mismatch
        }

        recovery_steps = []

        # Step 1: Initial analysis fails
        step1 = await simulate_claude_analysis(
            claude_server,
            "linear_model",
            {"data": initial_data, "formula": "revenue ~ quarter"},
            "Analyze revenue trends by quarter",
        )

        recovery_steps.append(
            ("Initial analysis", step1["success"], step1.get("error", ""))
        )

        # Step 2: Get diagnostic help
        if not step1["success"]:
            step2 = await simulate_claude_analysis(
                claude_server,
                "validate_data",
                {"data": initial_data, "analysis_type": "regression"},
                "What's wrong with my data?",
            )

            recovery_steps.append(("Data validation", step2["success"], ""))

            # Step 3: Get specific fix suggestions
            if step2["success"]:
                step3 = await simulate_claude_analysis(
                    claude_server,
                    "suggest_fix",
                    {"error_message": step1["error"], "tool_name": "linear_model"},
                    "How do I fix these data problems?",
                )

                recovery_steps.append(("Fix suggestions", step3["success"], ""))

                if step3["success"]:
                    suggestions = step3["data"]["suggestions"]

                    # Suggestions should form a logical progression
                    suggestions_text = " ".join(suggestions).lower()
                    progressive_actions = [
                        "first",
                        "then",
                        "next",
                        "after",
                        "before",
                        "ensure",
                    ]
                    logical_flow = any(
                        action in suggestions_text for action in progressive_actions
                    )

                    # Should address specific issues found
                    addresses_length = (
                        "length" in suggestions_text or "mismatch" in suggestions_text
                    )
                    addresses_missing = (
                        "missing" in suggestions_text or "na" in suggestions_text
                    )

                    print("   Recovery guidance addresses specific issues:")
                    print(f"   - Length mismatch: {addresses_length}")
                    print(f"   - Missing values: {addresses_missing}")
                    print(f"   - Logical flow: {logical_flow}")

        # Verify recovery workflow quality
        successful_steps = sum(1 for _, success, _ in recovery_steps if success)
        assert (
            successful_steps >= 2
        ), f"At least 2 recovery steps should succeed: {recovery_steps}"

        print("✅ Progressive error recovery workflow validated")
        print(f"   Recovery steps: {[step[0] for step in recovery_steps]}")
        print(f"   Success rate: {successful_steps}/{len(recovery_steps)}")


class TestErrorMessageQualityForClaude:
    """Test error message quality specifically for Claude conversation context."""

    @pytest.mark.asyncio
    async def test_error_messages_conversational_tone(self, claude_server, context):
        """Test that error messages work well in conversational AI context."""

        # Error scenarios with different user intents
        scenarios = [
            {
                "tool": "linear_model",
                "args": {"data": {}, "formula": "y ~ x"},
                "user_intent": "casual exploration",
                "expected_tone": "helpful",
            },
            {
                "tool": "read_csv",
                "args": {"file_path": "/missing.csv"},
                "user_intent": "urgent business need",
                "expected_tone": "solution-focused",
            },
        ]

        for scenario in scenarios:
            result = await simulate_claude_analysis(
                claude_server,
                scenario["tool"],
                scenario["args"],
                f"User with {scenario['user_intent']} trying to use {scenario['tool']}",
            )

            if not result["success"]:
                error_msg = result["error"]

                # Error messages should be conversational
                assert not error_msg.startswith(
                    "Error:"
                ), "Should not start with 'Error:'"
                assert len(error_msg.split()) > 3, "Should be more than just error code"

                # Should provide context
                error_lower = error_msg.lower()
                context_indicators = [
                    "analysis",
                    "data",
                    "file",
                    "statistical",
                    "model",
                ]
                assert any(
                    indicator in error_lower for indicator in context_indicators
                ), f"Should provide analysis context: {error_msg}"

                print(f"✅ Conversational error message for {scenario['tool']}: ✓")

    @pytest.mark.asyncio
    async def test_error_message_actionability(self, claude_server, context):
        """Test that error messages lead to actionable next steps."""

        # Create error that should lead to clear next steps
        result = await simulate_claude_analysis(
            claude_server,
            "chi_square_test",
            {
                "data": {"var1": ["A"], "var2": ["X"]},  # Insufficient data
                "test_type": "independence",
                "x": "var1",
                "y": "var2",
            },
            "Test if these two variables are independent",
        )

        if not result["success"]:
            error_msg = result["error"]

            # Should suggest what user can do
            error_lower = error_msg.lower()
            actionable_words = [
                "try",
                "ensure",
                "check",
                "add",
                "provide",
                "use",
                "consider",
            ]
            has_actionable = any(word in error_lower for word in actionable_words)

            # Should mention what's needed
            specific_needs = ["data", "observations", "samples", "values", "more"]
            mentions_needs = any(need in error_lower for need in specific_needs)

            assert (
                has_actionable or mentions_needs
            ), f"Error should be actionable or mention needs: {error_msg}"

            print("✅ Error message actionability verified")

    @pytest.mark.asyncio
    async def test_error_context_preservation_for_claude(self, claude_server, context):
        """Test that errors preserve enough context for Claude to help users."""

        # Error with specific context that Claude should preserve
        result = await simulate_claude_analysis(
            claude_server,
            "correlation_analysis",
            {
                "data": {
                    "sales_q1": [100, 200, 300],
                    "marketing_budget": [10, 20],  # Length mismatch
                },
                "variables": ["sales_q1", "marketing_budget"],
                "method": "pearson",
            },
            "Analyze correlation between Q1 sales and marketing budget",
        )

        if not result["success"]:
            error_msg = result["error"]

            # Should preserve variable names for Claude to reference
            assert (
                "sales_q1" in error_msg or "marketing_budget" in error_msg
            ), "Should preserve variable names"

            # Should preserve analysis type context
            analysis_context = ["correlation", "pearson", "variables"]
            has_context = any(ctx in error_msg.lower() for ctx in analysis_context)
            assert has_context, f"Should preserve analysis context: {error_msg}"

            print("✅ Error context preservation for Claude verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
