#!/bin/bash
# Development testing script

echo "🧪 Running RMCP test suite..."

# Run realistic user scenarios
echo "🎯 Running realistic user scenarios..."
python tests/realistic_scenarios.py || {
    echo "❌ User scenarios failed."
    exit 1
}

# Run unit tests with coverage (if any pytest files exist)
echo "📊 Running unit tests with coverage..."
if ls tests/test_*.py 1> /dev/null 2>&1; then
    pytest --cov=rmcp --cov-report=term-missing --cov-report=html tests/ || {
        echo "❌ Unit tests failed."
        exit 1
    }
    echo "📈 Coverage report generated in htmlcov/"
else
    echo "ℹ️  No pytest unit tests found (using realistic scenarios instead)"
fi

echo "✅ All tests passed!"