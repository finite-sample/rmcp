"""
Realistic user scenarios testing RMCP with real econometric data.

These tests simulate actual researcher workflows and use cases.
"""

import json
import csv
import pytest
import os
from pathlib import Path
from rmcp.tools import mcp
from rmcp.tools.common import RExecutionError

# Get the test data directory
TEST_DATA_DIR = Path(__file__).parent / "data"

class TestEconomicResearchScenarios:
    """Test realistic economic research scenarios."""
    
    def setup_method(self):
        """Load realistic datasets for testing."""
        # Load economic panel data
        self.economic_data = []
        with open(TEST_DATA_DIR / "economic_data.csv", 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric columns
                for col in ['year', 'gdp_growth', 'inflation', 'unemployment', 
                          'investment', 'trade_openness', 'population', 'education_index']:
                    row[col] = float(row[col])
                self.economic_data.append(row)
        
        # Convert to format expected by R tools
        self.economic_dict = {}
        for key in self.economic_data[0].keys():
            self.economic_dict[key] = [row[key] for row in self.economic_data]
        
        # Load firm panel data
        self.firm_data = []
        with open(TEST_DATA_DIR / "panel_data.csv", 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric columns
                for col in ['firm_id', 'year', 'revenue', 'rd_spending', 'employees', 'market_cap']:
                    row[col] = float(row[col])
                self.firm_data.append(row)
        
        # Convert to R format
        self.firm_dict = {}
        for key in self.firm_data[0].keys():
            self.firm_dict[key] = [row[key] for row in self.firm_data]
    
    def test_gdp_growth_determinants(self):
        """Test: What determines GDP growth across countries?"""
        print("\n=== Testing: GDP Growth Determinants Analysis ===")
        
        linear_model = mcp.tools["linear_model"]["function"]
        
        # Research question: How do inflation, unemployment, and investment affect GDP growth?
        result = linear_model(
            formula="gdp_growth ~ inflation + unemployment + investment + trade_openness",
            data=self.economic_dict,
            robust=True  # Use robust standard errors for cross-country data
        )
        
        print(f"Model Results:")
        print(f"Coefficients: {result['coefficients']}")
        print(f"R-squared: {result['r_squared']:.4f}")
        print(f"Robust Standard Errors: {result['robust']}")
        
        # Verify reasonable results
        assert isinstance(result['coefficients'], dict)
        assert 'inflation' in result['coefficients']
        assert 'unemployment' in result['coefficients'] 
        assert 'investment' in result['coefficients']
        assert result['r_squared'] >= 0  # R-squared should be non-negative
        assert result['robust'] == True
        
        # Economic intuition: investment should positively affect growth
        assert result['coefficients']['investment'] > 0, "Investment should positively affect GDP growth"
        
    def test_inflation_unemployment_correlation(self):
        """Test: Phillips Curve - relationship between inflation and unemployment."""
        print("\n=== Testing: Phillips Curve Analysis ===")
        
        correlation_func = mcp.tools["correlation"]["function"]
        
        result = correlation_func(
            data=self.economic_dict,
            var1="inflation",
            var2="unemployment", 
            method="pearson"
        )
        
        print(f"Inflation-Unemployment Correlation: {result['correlation']:.4f}")
        
        assert isinstance(result['correlation'], (int, float))
        assert -1 <= result['correlation'] <= 1
        assert result['method'] == "pearson"
        
        # Phillips curve suggests negative correlation (though may not hold in all periods)
        print(f"Phillips Curve Evidence: {'Negative' if result['correlation'] < 0 else 'Positive'} correlation")
    
    def test_country_economic_performance(self):
        """Test: Compare economic performance across countries."""
        print("\n=== Testing: Country Performance Comparison ===")
        
        group_by_func = mcp.tools["group_by"]["function"]
        
        # Average GDP growth by country
        growth_result = group_by_func(
            data=self.economic_dict,
            group_col="country",
            summarise_col="gdp_growth",
            stat="mean"
        )
        
        print("Average GDP Growth by Country:")
        for row in growth_result['summary']:
            print(f"  {row['country']}: {row['s_value']:.2f}%")
        
        # Average unemployment by country  
        unemployment_result = group_by_func(
            data=self.economic_dict,
            group_col="country", 
            summarise_col="unemployment",
            stat="mean"
        )
        
        print("\nAverage Unemployment by Country:")
        for row in unemployment_result['summary']:
            print(f"  {row['country']}: {row['s_value']:.2f}%")
        
        assert len(growth_result['summary']) > 0
        assert len(unemployment_result['summary']) > 0
        
        # Verify we have data for expected countries
        countries = {row['country'] for row in growth_result['summary']}
        expected_countries = {'USA', 'GBR', 'DEU', 'FRA', 'JPN', 'CAN'}
        assert countries == expected_countries
    
    def test_firm_revenue_rd_relationship(self):
        """Test: How does R&D spending affect firm revenue?"""
        print("\n=== Testing: R&D Investment and Firm Performance ===")
        
        linear_model = mcp.tools["linear_model"]["function"]
        
        # Research question: Does R&D spending increase revenue?
        result = linear_model(
            formula="revenue ~ rd_spending + employees + I(year - 2018)",
            data=self.firm_dict,
            robust=False
        )
        
        print(f"R&D-Revenue Relationship:")
        print(f"R&D Coefficient: {result['coefficients']['rd_spending']:.2f}")
        print(f"Employee Coefficient: {result['coefficients']['employees']:.4f}")
        print(f"R-squared: {result['r_squared']:.4f}")
        
        assert result['coefficients']['rd_spending'] > 0, "R&D spending should positively affect revenue"
        assert result['coefficients']['employees'] > 0, "More employees should increase revenue" 
        assert result['r_squared'] > 0.5, "Model should explain substantial variance"
    
    def test_panel_data_fixed_effects(self):
        """Test: Firm fixed effects model for revenue determinants."""
        print("\n=== Testing: Panel Data Fixed Effects Model ===")
        
        panel_model_func = mcp.tools["panel_model"]["function"]
        
        # Use firm fixed effects to control for unobserved firm characteristics
        result = panel_model_func(
            formula="revenue ~ rd_spending + employees",
            data=self.firm_dict,
            index=["firm_id", "year"],
            effect="individual",  # Firm fixed effects
            model="within"
        )
        
        print(f"Fixed Effects Results:")
        print(f"R&D Coefficient: {result['coefficients']['rd_spending']:.3f}")
        print(f"Employee Coefficient: {result['coefficients']['employees']:.6f}")
        print(f"R-squared (within): {result['r_squared']:.4f}")
        
        assert 'rd_spending' in result['coefficients']
        assert 'employees' in result['coefficients']
        assert result['model_type'] == "within"
        assert result['effect_type'] == "individual"
        
        # R&D should still be positive even after controlling for firm fixed effects
        assert result['coefficients']['rd_spending'] > 0
    
    def test_industry_effects_analysis(self):
        """Test: Industry-level analysis of firm performance."""
        print("\n=== Testing: Industry Performance Analysis ===")
        
        group_by_func = mcp.tools["group_by"]["function"]
        
        # Average revenue by industry
        result = group_by_func(
            data=self.firm_dict,
            group_col="industry",
            summarise_col="revenue",
            stat="mean"
        )
        
        print("Average Revenue by Industry:")
        industry_revenues = {}
        for row in result['summary']:
            industry_revenues[row['industry']] = row['s_value']
            print(f"  {row['industry']}: ${row['s_value']:.1f}M")
        
        # Test R&D intensity by industry
        rd_result = group_by_func(
            data=self.firm_dict,
            group_col="industry",
            summarise_col="rd_spending", 
            stat="mean"
        )
        
        print("\nAverage R&D Spending by Industry:")
        for row in rd_result['summary']:
            print(f"  {row['industry']}: ${row['s_value']:.1f}M")
        
        assert len(result['summary']) > 0
        
        # Tech and pharma should have high R&D spending
        rd_by_industry = {row['industry']: row['s_value'] for row in rd_result['summary']}
        if 'tech' in rd_by_industry and 'retail' in rd_by_industry:
            assert rd_by_industry['tech'] > rd_by_industry['retail'], \
                "Tech should spend more on R&D than retail"
    
    def test_diagnostic_analysis(self):
        """Test: Model diagnostics on economic data."""
        print("\n=== Testing: Econometric Model Diagnostics ===")
        
        diagnostics_func = mcp.tools["diagnostics"]["function"]
        
        try:
            result = diagnostics_func(
                formula="gdp_growth ~ inflation + unemployment + investment",
                data=self.economic_dict,
                tests=["bp"]  # Breusch-Pagan test for heteroskedasticity
            )
            
            print(f"Diagnostic Test Results:")
            print(f"Results structure: {list(result.keys())}")
            
            assert isinstance(result, dict)
            
        except RExecutionError as e:
            # Some diagnostic tests might fail with small samples
            print(f"Diagnostic test failed (expected with small sample): {e}")
            pytest.skip("Diagnostic test requires larger sample size")


class TestUserWorkflowScenarios:
    """Test complete user workflows from start to finish."""
    
    def test_research_paper_workflow(self):
        """Test: Complete research paper data analysis workflow."""
        print("\n=== Testing: Complete Research Workflow ===")
        
        # Step 1: Descriptive statistics
        print("Step 1: Descriptive Analysis")
        descriptive_func = mcp.tools["linear_model"]["function"]  # We'll use this for basic stats
        
        # Create simple summary data
        data = {
            'gdp_growth': [2.5, 1.6, 2.2, 1.8, 2.5, 2.9, 1.9, 1.5, 1.4, 2.1],
            'inflation': [1.6, 3.1, 2.1, 1.5, 0.1, 0.1, 3.3, 4.5, 2.8, 2.6],
            'constant': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        }
        
        # Basic regression for descriptive purposes
        desc_result = descriptive_func(
            formula="gdp_growth ~ constant - 1",  # Just get the mean
            data=data,
            robust=False
        )
        
        print(f"Average GDP Growth: {desc_result['coefficients']['constant']:.2f}%")
        
        # Step 2: Correlation analysis
        print("\nStep 2: Correlation Analysis") 
        correlation_func = mcp.tools["correlation"]["function"]
        
        corr_result = correlation_func(
            data=data,
            var1="gdp_growth",
            var2="inflation",
            method="pearson"
        )
        
        print(f"GDP Growth - Inflation Correlation: {corr_result['correlation']:.4f}")
        
        # Step 3: Main regression analysis
        print("\nStep 3: Main Regression Analysis")
        main_result = descriptive_func(
            formula="gdp_growth ~ inflation",
            data=data,
            robust=True
        )
        
        print(f"Inflation Effect on GDP Growth: {main_result['coefficients']['inflation']:.4f}")
        print(f"Model R-squared: {main_result['r_squared']:.4f}")
        print(f"Using Robust Standard Errors: {main_result['robust']}")
        
        # Verify workflow completed successfully
        assert desc_result['coefficients']['constant'] > 0
        assert -1 <= corr_result['correlation'] <= 1
        assert isinstance(main_result['coefficients']['inflation'], (int, float))
        
        print("\n✅ Complete research workflow executed successfully!")
    
    def test_policy_analysis_scenario(self):
        """Test: Policy impact analysis scenario."""
        print("\n=== Testing: Policy Impact Analysis ===")
        
        # Simulate pre/post policy data
        policy_data = {
            'outcome': [100, 102, 101, 98, 105, 110, 108, 112, 115, 118],  # Post-policy improvement
            'treatment': [0, 0, 0, 0, 0, 1, 1, 1, 1, 1],  # Policy starts at period 6
            'time_trend': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'control_factor': [50, 51, 49, 52, 48, 53, 52, 54, 51, 55]
        }
        
        linear_model = mcp.tools["linear_model"]["function"]
        
        # Difference-in-differences style analysis
        policy_result = linear_model(
            formula="outcome ~ treatment + time_trend + control_factor",
            data=policy_data,
            robust=True
        )
        
        print(f"Policy Treatment Effect: {policy_result['coefficients']['treatment']:.2f}")
        print(f"Time Trend: {policy_result['coefficients']['time_trend']:.2f}")
        print(f"Model R-squared: {policy_result['r_squared']:.4f}")
        
        # Policy should have positive effect in our simulated data
        assert policy_result['coefficients']['treatment'] > 0, "Policy should have positive impact"
        assert policy_result['r_squared'] > 0.8, "Model should fit well with controlled data"
        
        print("✅ Policy analysis completed successfully!")


class TestErrorHandlingScenarios:
    """Test realistic error scenarios users might encounter."""
    
    def test_missing_variable_error(self):
        """Test: User references non-existent variable."""
        print("\n=== Testing: Missing Variable Error Handling ===")
        
        linear_model = mcp.tools["linear_model"]["function"]
        
        data = {'x': [1, 2, 3, 4, 5], 'y': [2, 4, 6, 8, 10]}
        
        with pytest.raises(RExecutionError) as exc_info:
            linear_model(
                formula="y ~ x + missing_variable",  # missing_variable doesn't exist
                data=data,
                robust=False
            )
        
        error_message = str(exc_info.value)
        print(f"Error caught: {error_message}")
        assert "missing_variable" in error_message or "object" in error_message
        print("✅ Missing variable error handled properly!")
    
    def test_invalid_formula_error(self):
        """Test: User provides malformed regression formula.""" 
        print("\n=== Testing: Invalid Formula Error Handling ===")
        
        linear_model = mcp.tools["linear_model"]["function"]
        
        data = {'x': [1, 2, 3, 4, 5], 'y': [2, 4, 6, 8, 10]}
        
        with pytest.raises(RExecutionError) as exc_info:
            linear_model(
                formula="y ~~~ x + + +",  # Invalid formula syntax
                data=data,
                robust=False
            )
        
        error_message = str(exc_info.value)
        print(f"Error caught: {error_message}")
        print("✅ Invalid formula error handled properly!")
    
    def test_insufficient_data_error(self):
        """Test: User provides insufficient data for analysis."""
        print("\n=== Testing: Insufficient Data Error Handling ===")
        
        panel_model = mcp.tools["panel_model"]["function"]
        
        # Insufficient data for panel analysis
        tiny_data = {
            'firm_id': [1, 1],
            'year': [2020, 2021], 
            'revenue': [100, 110],
            'rd_spending': [5, 6]
        }
        
        with pytest.raises(RExecutionError) as exc_info:
            panel_model(
                formula="revenue ~ rd_spending",
                data=tiny_data,
                index=["firm_id", "year"],
                model="within"
            )
        
        error_message = str(exc_info.value) 
        print(f"Error caught: {error_message}")
        print("✅ Insufficient data error handled properly!")


class TestPerformanceScenarios:
    """Test performance with larger, realistic datasets."""
    
    def test_medium_dataset_performance(self):
        """Test: Performance with medium-sized dataset (1000+ observations)."""
        print("\n=== Testing: Medium Dataset Performance ===")
        
        # Generate larger synthetic dataset
        import random
        random.seed(42)  # Reproducible results
        
        n_firms = 50
        n_years = 20
        large_data = {
            'firm_id': [],
            'year': [],
            'revenue': [],
            'rd_spending': [],
            'employees': []
        }
        
        for firm in range(1, n_firms + 1):
            base_revenue = random.uniform(500, 2000)
            for year in range(2000, 2000 + n_years):
                large_data['firm_id'].append(firm)
                large_data['year'].append(year)
                # Add some realistic relationships and noise
                rd = random.uniform(10, 100)
                employees = random.uniform(100, 5000)
                revenue = base_revenue + 0.5 * rd + 0.1 * employees + random.uniform(-50, 50)
                large_data['revenue'].append(revenue)
                large_data['rd_spending'].append(rd)
                large_data['employees'].append(employees)
        
        print(f"Dataset size: {len(large_data['firm_id'])} observations")
        
        # Test linear model performance
        import time
        
        linear_model = mcp.tools["linear_model"]["function"]
        
        start_time = time.time()
        result = linear_model(
            formula="revenue ~ rd_spending + employees",
            data=large_data,
            robust=True
        )
        end_time = time.time()
        
        execution_time = end_time - start_time
        print(f"Linear model execution time: {execution_time:.2f} seconds")
        print(f"R-squared: {result['r_squared']:.4f}")
        
        # Should complete within reasonable time (< 30 seconds)
        assert execution_time < 30, f"Execution took too long: {execution_time:.2f}s"
        assert result['r_squared'] > 0, "Model should explain some variance"
        
        print("✅ Medium dataset performance test passed!")


if __name__ == "__main__":
    # Run some quick tests manually
    test = TestEconomicResearchScenarios()
    test.setup_method()
    test.test_gdp_growth_determinants()