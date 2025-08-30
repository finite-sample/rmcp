#!/bin/bash
# Development testing script

echo "🧪 Running RMCP test suite..."

# Run MCP interface tests (what AI assistants actually use)
echo "🗣️ Testing MCP conversational interface..."
python tests/test_mcp_interface.py || {
    echo "❌ MCP interface tests failed."
    exit 1
}

# Run realistic user scenarios
echo "🎯 Running realistic user scenarios..."
python tests/realistic_scenarios.py || {
    echo "❌ User scenarios failed."
    exit 1
}

# Note: We use comprehensive integration tests rather than unit tests
echo "ℹ️  Using integration tests (MCP + realistic scenarios) instead of unit tests"
echo "📊 Coverage: Validated through end-to-end conversational flows"

echo "✅ All tests passed!"
echo "🗣️ Conversational interface validated!"
echo "📊 User scenarios validated!"