#!/bin/bash
# Development testing script

echo "🧪 Running RMCP test suite..."

# Run unit tests with coverage
echo "📊 Running unit tests with coverage..."
pytest --cov=rmcp --cov-report=term-missing --cov-report=html tests/ || {
    echo "❌ Unit tests failed."
    exit 1
}

# Run integration tests  
echo "🔗 Running integration tests..."
./tests/test_all_tools.sh || {
    echo "❌ Integration tests failed."
    exit 1
}

# Run CLI tests
echo "🖥️  Running CLI tests..."
./tests/run_cli_tests.sh || {
    echo "❌ CLI tests failed."
    exit 1
}

echo "✅ All tests passed!"
echo "📈 Coverage report generated in htmlcov/"