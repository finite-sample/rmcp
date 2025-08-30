#!/bin/bash
# Development linting script

echo "🔍 Running code quality checks..."

echo "📝 Formatting with black..."
black --check rmcp tests || {
    echo "❌ Black formatting issues found. Run 'black rmcp tests' to fix."
    exit 1
}

echo "📦 Checking import order with isort..."
isort --check-only rmcp tests || {
    echo "❌ Import order issues found. Run 'isort rmcp tests' to fix."
    exit 1
}

echo "🔍 Linting with flake8..."
flake8 rmcp tests || {
    echo "❌ Flake8 issues found."
    exit 1
}

echo "🔍 Type checking with mypy..."
mypy rmcp || {
    echo "❌ Type checking issues found."
    exit 1
}

echo "✅ All code quality checks passed!"