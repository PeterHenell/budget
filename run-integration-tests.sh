#!/bin/bash

# Integration Test Runner - Budget App  
# Runs tests that require database connection
# These tests must run inside Docker containers with database access

set -e  # Exit on error

echo "🔗 Running Integration Tests (Database Required)"
echo "==============================================="

# Check if we're running inside Docker container
if [[ -f "/.dockerenv" ]]; then
    echo "✅ Running inside Docker container"
    DOCKER_MODE=true
else
    echo "🐳 Running on host - will use Docker container for tests"
    DOCKER_MODE=false
fi
export ENVIRONMENT=test

# Function to run tests in Docker
run_in_docker() {
    echo "🚀 Starting Docker services..."
    docker compose up -d
    
    # Wait for services to be ready
    echo "⏳ Waiting for services to be ready..."
    sleep 10
    
    # Run integration tests inside container
    echo "🔍 Running Integration Tests in Docker..."
    docker compose exec web bash -c "
        cd /app &&
        python -m pytest tests/integration/ -v --tb=short
    "
    
    echo "🛑 Stopping Docker services..."
    docker compose down
}

# Function to run tests locally (if inside Docker)
run_locally() {
    echo "🔍 Running Integration Tests..."
    echo "Tests location: tests/integration/"
    echo "Test files:"
    find tests/integration/ -name "test_*.py" | sed 's/^/  /'
    
    echo -e "\n🚀 Executing tests..."
    python -m pytest tests/integration/ -v --tb=short
}

# Main execution
if [[ "$DOCKER_MODE" == "true" ]]; then
    run_locally
else
    run_in_docker
fi

echo -e "\n✅ Integration Tests Complete!"
echo "These tests verify system integration with real database connections."
