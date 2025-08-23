#!/bin/bash

# Unit Test Runner - Budget App
# Runs tests that don't require database connection
# These tests use mocks and can run in any environment

set -e  # Exit on error

echo "🧪 Running Unit Tests (No Database Required)"
echo "============================================="

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not detected. Activating..."
    if [[ -f "venv/bin/activate" ]]; then
        source venv/bin/activate
        echo "✅ Virtual environment activated"
    else
        echo "❌ Virtual environment not found. Please run: python -m venv venv && source venv/bin/activate"
        exit 1
    fi
fi


export ENVIRONMENT=test

# Install dependencies if needed
echo "📦 Checking dependencies..."
pip install -q -r src/requirements.txt

# Change to project directory if not already there
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Run unit tests with pytest
echo -e "\n🔍 Running Unit Tests..."
echo "Tests location: tests/unit/"
echo "Test files:"
find tests/unit/ -name "test_*.py" | sed 's/^/  /'

echo -e "\n🚀 Executing tests..."
python -m pytest tests/unit/ -v --tb=short

echo -e "\n✅ Unit Tests Complete!"
echo "These tests verify business logic using mocks and don't require database connectivity."
