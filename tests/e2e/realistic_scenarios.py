"""
Realistic user scenarios testing the RMCP MCP server.

Tests what real users want to accomplish:
- Business analyst: Sales prediction model
- Economist: Market relationship analysis
- Data scientist: Customer behavior modeling
- Researcher: Treatment effect analysis

Each test uses the new MCP architecture with proper tools.
"""

import asyncio
import sys
from pathlib import Path

# Add rmcp to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rmcp.tools.regression import (
    linear_model,
    correlation_analysis,
    logistic_regression,
)
from rmcp.core.context import Context, LifespanState


async def create_test_context():
    """Create a test context for tool execution."""
    lifespan = LifespanState()
    context = Context.create("test", "test", lifespan)
    return context


async def test_business_analyst_scenario():
    """Business analyst wants to predict sales from marketing spend."""

    print("📊 Business Analyst Scenario: Sales Prediction")
    print("-" * 50)

    # Realistic quarterly sales data
    sales_data = {
        "sales": [
            120,
            135,
            128,
            142,
            156,
            148,
            160,
            175,
            168,
            180,
            165,
            172,
            185,
            178,
            192,
            188,
        ],
        "marketing": [10, 12, 11, 14, 16, 15, 18, 20, 19, 22, 17, 19, 23, 21, 25, 24],
        "quarter": [1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4],
        "year": [
            2021,
            2021,
            2021,
            2021,
            2022,
            2022,
            2022,
            2022,
            2023,
            2023,
            2023,
            2023,
            2024,
            2024,
            2024,
            2024,
        ],
    }

    try:
        context = await create_test_context()

        # Question: "How much does marketing spend affect sales?"
        result = await linear_model(
            context, {"data": sales_data, "formula": "sales ~ marketing + quarter"}
        )

        # Business validation
        r_squared = result["r_squared"]
        marketing_effect = result["coefficients"]["marketing"]
        marketing_pvalue = result["p_values"]["marketing"]

        print(f"✅ Sales Model Results:")
        print(f"   📈 Marketing ROI: ${marketing_effect:.2f} sales per $1 marketing")
        print(f"   📊 Model explains {r_squared:.1%} of sales variation")
        print(f"   🎯 Marketing effect p-value: {marketing_pvalue:.4f}")
        print(f"   📋 Sample size: {result['n_obs']} quarters")

        # Business success criteria
        assert marketing_effect > 0, "Marketing should increase sales"
        assert marketing_pvalue < 0.05, "Marketing effect should be significant"
        assert r_squared > 0.8, "Model should explain >80% of variance"

        print("✅ PASS: Business analyst can predict sales effectively")
        return True

    except Exception as e:
        print(f"❌ FAIL: Business scenario error - {e}")
        return False


async def test_economist_scenario():
    """Economist wants to analyze GDP, inflation, and unemployment relationships."""

    print("\n🏛️ Economist Scenario: Macroeconomic Analysis")
    print("-" * 50)

    # Realistic macroeconomic time series
    macro_data = {
        "gdp_growth": [2.1, 2.3, 1.8, 2.5, 2.7, 2.2, 1.9, 2.4, 2.6, 2.1, 1.7, 2.0],
        "inflation": [1.5, 1.8, 2.1, 1.9, 2.3, 2.0, 1.7, 2.2, 2.4, 1.8, 1.6, 1.9],
        "unemployment": [5.2, 5.0, 5.5, 4.8, 4.5, 4.9, 5.3, 4.7, 4.4, 5.1, 5.4, 5.0],
        "quarter": [
            "Q1-21",
            "Q2-21",
            "Q3-21",
            "Q4-21",
            "Q1-22",
            "Q2-22",
            "Q3-22",
            "Q4-22",
            "Q1-23",
            "Q2-23",
            "Q3-23",
            "Q4-23",
        ],
    }

    try:
        context = await create_test_context()

        # Question: "What are the relationships between key macro variables?"
        corr_result = await correlation_analysis(
            context,
            {
                "data": macro_data,
                "variables": ["gdp_growth", "inflation", "unemployment"],
                "method": "pearson",
            },
        )

        # Economic theory validation
        corr_matrix = corr_result["correlation_matrix"]

        # Okun's Law: GDP growth and unemployment should be negatively correlated
        gdp_unemp_corr = corr_matrix["gdp_growth"][
            2
        ]  # unemployment is 3rd variable (index 2)

        print(f"✅ Macroeconomic Correlations:")
        print(f"   📉 GDP-Unemployment: {gdp_unemp_corr:.3f} (Okun's Law)")
        print(f"   📊 Sample size: {corr_result['n_obs']} observations")
        print(f"   🔬 Variables analyzed: {', '.join(corr_result['variables'])}")

        # Test Phillips Curve: inflation ~ unemployment
        phillips_result = await linear_model(
            context, {"data": macro_data, "formula": "inflation ~ unemployment"}
        )

        phillips_coef = phillips_result["coefficients"]["unemployment"]
        phillips_r2 = phillips_result["r_squared"]

        print(f"   📈 Phillips Curve slope: {phillips_coef:.3f}")
        print(f"   📊 Phillips R²: {phillips_r2:.3f}")

        # Economic validation
        assert (
            gdp_unemp_corr < 0
        ), "GDP growth and unemployment should be negatively correlated"

        print("✅ PASS: Economist can analyze macroeconomic relationships")
        return True

    except Exception as e:
        print(f"❌ FAIL: Economist scenario error - {e}")
        return False


async def test_data_scientist_scenario():
    """Data scientist wants to predict customer churn."""

    print("\n🤖 Data Scientist Scenario: Customer Churn Prediction")
    print("-" * 50)

    # Realistic customer churn data
    churn_data = {
        "churn": [0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1],
        "tenure_months": [
            24,
            6,
            36,
            3,
            48,
            18,
            9,
            2,
            60,
            4,
            30,
            7,
            42,
            5,
            54,
            15,
            8,
            1,
            66,
            6,
        ],
        "monthly_charges": [
            70,
            85,
            65,
            90,
            60,
            75,
            95,
            100,
            55,
            88,
            68,
            92,
            62,
            87,
            58,
            78,
            93,
            105,
            52,
            89,
        ],
        "support_tickets": [0, 3, 1, 5, 0, 1, 4, 6, 0, 4, 1, 5, 0, 3, 0, 2, 4, 7, 0, 3],
    }

    try:
        context = await create_test_context()

        # Question: "Can I predict which customers will churn?"
        churn_model = await logistic_regression(
            context,
            {
                "data": churn_data,
                "formula": "churn ~ tenure_months + monthly_charges + support_tickets",
                "family": "binomial",
                "link": "logit",
            },
        )

        # Model performance validation
        accuracy = churn_model.get("accuracy", 0)
        mcfadden_r2 = churn_model.get("mcfadden_r_squared", 0)
        tenure_coef = churn_model["coefficients"]["tenure_months"]
        support_coef = churn_model["coefficients"]["support_tickets"]

        print(f"✅ Churn Prediction Model:")
        print(f"   🎯 Accuracy: {accuracy:.1%}")
        print(f"   📊 McFadden R²: {mcfadden_r2:.3f}")
        print(f"   📉 Tenure effect: {tenure_coef:.4f} (longer tenure = less churn)")
        print(f"   📞 Support tickets effect: {support_coef:.4f}")
        print(f"   📋 Sample size: {churn_model['n_obs']} customers")

        # Data science validation
        assert accuracy > 0.6, "Model should achieve >60% accuracy"
        assert tenure_coef < 0, "Longer tenure should reduce churn probability"
        assert (
            support_coef > 0
        ), "More support tickets should increase churn probability"

        print("✅ PASS: Data scientist can build churn prediction model")
        return True

    except Exception as e:
        print(f"❌ FAIL: Data science scenario error - {e}")
        return False


async def test_researcher_scenario():
    """Academic researcher wants to test treatment effects."""

    print("\n🔬 Research Scenario: Treatment Effect Analysis")
    print("-" * 50)

    # Controlled experiment data with clear treatment effect
    experiment_data = {
        "outcome": [
            4.2,
            6.8,
            3.8,
            7.1,
            4.1,
            6.9,
            3.5,
            7.3,
            4.5,
            6.7,
            4.0,
            7.2,
            3.9,
            6.8,
            4.3,
            7.0,
        ],
        "treatment": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
        "age": [25, 30, 22, 35, 28, 33, 24, 38, 26, 36, 27, 34, 29, 32, 25, 37],
        "baseline_score": [
            3.8,
            4.2,
            3.5,
            4.8,
            4.1,
            4.5,
            3.2,
            5.1,
            4.0,
            4.7,
            3.9,
            4.9,
            3.7,
            4.4,
            4.2,
            4.6,
        ],
    }

    try:
        context = await create_test_context()

        # Question: "What is the treatment effect controlling for covariates?"
        treatment_model = await linear_model(
            context,
            {
                "data": experiment_data,
                "formula": "outcome ~ treatment + age + baseline_score",
            },
        )

        # Research validation
        treatment_coef = treatment_model["coefficients"]["treatment"]
        treatment_pvalue = treatment_model["p_values"]["treatment"]
        baseline_coef = treatment_model["coefficients"]["baseline_score"]
        r_squared = treatment_model["r_squared"]

        print(f"✅ Treatment Effect Results:")
        print(f"   🧪 Treatment effect: {treatment_coef:.3f} points")
        print(f"   📊 Significance: p = {treatment_pvalue:.4f}")
        print(f"   📈 Baseline control: {baseline_coef:.3f}")
        print(f"   🎯 Model R²: {r_squared:.3f}")
        print(f"   👥 Sample size: {treatment_model['n_obs']} participants")

        # Research standards
        assert treatment_coef > 0, "Treatment should have positive effect"
        assert (
            treatment_pvalue < 0.05
        ), "Treatment effect should be statistically significant"
        assert baseline_coef > 0, "Baseline should predict outcome"
        assert r_squared > 0.7, "Model should have good explanatory power"

        print("✅ PASS: Researcher can analyze treatment effects")
        return True

    except Exception as e:
        print(f"❌ FAIL: Research scenario error - {e}")
        return False


async def run_all_scenarios():
    """Run all realistic user scenarios."""

    print("🎯 RMCP MCP Server - Realistic User Testing")
    print("=" * 55)
    print("Testing what real users want to accomplish with R analysis\n")

    scenarios = [
        ("Business Analyst", test_business_analyst_scenario),
        ("Economist", test_economist_scenario),
        ("Data Scientist", test_data_scientist_scenario),
        ("Academic Researcher", test_researcher_scenario),
    ]

    results = []

    for scenario_name, test_func in scenarios:
        try:
            success = await test_func()
            results.append((scenario_name, success))
        except Exception as e:
            print(f"❌ {scenario_name} scenario crashed: {e}")
            results.append((scenario_name, False))

    # Summary
    print("\n" + "=" * 55)
    print("🎯 REALISTIC SCENARIO RESULTS")
    print("=" * 55)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for scenario_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {scenario_name}")

    print(f"\n📊 Overall Success Rate: {passed}/{total} ({passed/total:.1%})")

    if passed == total:
        print("🎉 ALL SCENARIOS PASSED!")
        print("✅ Users can accomplish their real-world R analysis goals")
        print("🚀 RMCP is ready for production use!")
    else:
        print("⚠️  SOME SCENARIOS FAILED")
        print("🔧 Need to fix issues before production deployment")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_scenarios())
    exit(0 if success else 1)
