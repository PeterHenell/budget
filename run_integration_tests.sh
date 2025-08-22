#!/bin/bash

# Integration Test Runner for Budget App
# This script runs comprehensive integration tests against the full application stack

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Budget App Integration Test Runner${NC}"
echo "======================================"

# Function to print colored output
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to cleanup on exit
cleanup() {
    log_info "Cleaning up test environment..."
    docker compose -f docker-compose.test.yml down -v --remove-orphans >/dev/null 2>&1 || true
}

# Set up cleanup trap
trap cleanup EXIT

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if required files exist
if [[ ! -f "docker-compose.test.yml" ]]; then
    log_error "docker-compose.test.yml not found in current directory"
    exit 1
fi

if [[ ! -f "tests/test_integration.py" ]]; then
    log_error "tests/test_integration.py not found"
    exit 1
fi

# Install test dependencies locally if needed
if [[ ! -d "venv" ]]; then
    log_info "Creating virtual environment for test dependencies..."
    python3 -m venv venv
fi

log_info "Installing/updating test dependencies..."
source venv/bin/activate
pip install -q requests pytest pytest-html

# Clean up any existing test containers
log_info "Cleaning up any existing test containers..."
docker compose -f docker-compose.test.yml down -v --remove-orphans >/dev/null 2>&1 || true

# Run integration tests
log_info "Starting integration tests..."
echo ""

# Change to directory containing the test file
cd "$(dirname "$0")"

# Run pytest with detailed output
python -m pytest tests/test_integration.py \
    -v \
    --tb=short \
    --html=test-report.html \
    --self-contained-html \
    --color=yes

# Check test results
TEST_EXIT_CODE=$?

if [[ $TEST_EXIT_CODE -eq 0 ]]; then
    log_success "All integration tests passed! 🎉"
    log_info "Test report generated: test-report.html"
else
    log_error "Some integration tests failed."
    log_info "Check test-report.html for detailed results"
    exit $TEST_EXIT_CODE
fi

echo ""
log_success "Integration test run completed successfully!"
log_info "Test containers will be cleaned up automatically."
