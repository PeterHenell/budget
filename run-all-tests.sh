#!/bin/bash

# Master Test Runner - Budget App
# Runs both unit tests and integration tests with summary

set -e  # Exit on error

echo "🧪🔗 Budget App - Full Test Suite"
echo "================================="
echo "This script runs both unit tests (no database) and integration tests (with database)"
echo ""

# Variables to track test results
UNIT_TESTS_PASSED=false
INTEGRATION_TESTS_PASSED=false

# Function to run unit tests
run_unit_tests() {
    echo "📋 PHASE 1: Unit Tests"
    echo "====================="
    if ./run-unit-tests.sh; then
        UNIT_TESTS_PASSED=true
        echo "✅ Unit tests PASSED"
    else
        echo "❌ Unit tests FAILED"
    fi
    echo ""
}

# Function to run integration tests
run_integration_tests() {
    echo "📋 PHASE 2: Integration Tests"
    echo "============================="
    if ./run-integration-tests.sh; then
        INTEGRATION_TESTS_PASSED=true
        echo "✅ Integration tests PASSED"
    else
        echo "❌ Integration tests FAILED"
    fi
    echo ""
}

# Main execution
echo "🚀 Starting full test suite..."
echo ""

# Run unit tests first (faster, no Docker required)
run_unit_tests

# Run integration tests (slower, requires Docker)
run_integration_tests

# Summary
echo "📊 TEST SUMMARY"
echo "==============="
if [[ "$UNIT_TESTS_PASSED" == "true" ]]; then
    echo "✅ Unit Tests: PASSED"
else
    echo "❌ Unit Tests: FAILED"
fi

if [[ "$INTEGRATION_TESTS_PASSED" == "true" ]]; then
    echo "✅ Integration Tests: PASSED"
else
    echo "❌ Integration Tests: FAILED"
fi

echo ""
if [[ "$UNIT_TESTS_PASSED" == "true" && "$INTEGRATION_TESTS_PASSED" == "true" ]]; then
    echo "🎉 ALL TESTS PASSED!"
    exit 0
else
    echo "⚠️  Some tests failed. Check output above for details."
    exit 1
fi
