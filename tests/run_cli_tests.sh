#!/bin/bash
set -e

echo "Testing 'rmcp version'..."
rmcp version

echo "Testing 'rmcp start' with test_request.json..."
cat tests/test_request.json | rmcp start

echo "Testing 'rmcp dev' with tests/dev_server.py..."
rmcp dev tests/dev_server.py

echo "All CLI tests passed."
