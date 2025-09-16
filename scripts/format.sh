#!/bin/bash
# Development formatting script

echo "🎨 Formatting RMCP codebase..."

echo "📝 Running black formatter..."
black rmcp tests

echo "📦 Sorting imports with isort..."
isort rmcp tests

echo "✅ Code formatting complete!"