#!/bin/bash

# Integration Test Runner - Budget App  
# Runs tests that require database connection
# These tests ALWAYS run inside Docker containers with database access
#
# Usage:
#   ./run-integration-tests.sh                              # Run all integration tests
#   ./run-integration-tests.sh -k "TestAuthentication"      # Run specific test class
#   ./run-integration-tests.sh -k "test_login"              # Run specific test method
#   ./run-integration-tests.sh --maxfail=1 -v               # Stop after first failure, verbose
#   ./run-integration-tests.sh -h                           # Show help
#
# All parameters are passed directly to pytest

set -e  # Exit on error

# Store all script arguments to pass to pytest
PYTEST_ARGS="$@"

# Show help if requested
if [[ "$*" == *"-h"* ]] || [[ "$*" == *"--help"* ]]; then
    echo "🔗 Integration Test Runner - Budget App"
    echo "==============================================="
    echo "Usage: $0 [pytest-options]"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run all integration tests"
    echo "  $0 -k 'TestAuthentication'           # Run specific test class"
    echo "  $0 -k 'test_login'                   # Run specific test method"
    echo "  $0 -k 'test_login_page_loads'        # Run single test"
    echo "  $0 --maxfail=1 -v                    # Stop after first failure, verbose"
    echo "  $0 --tb=short -q                     # Short traceback, quiet output"
    echo ""
    echo "Common pytest options:"
    echo "  -k EXPRESSION    # Run tests matching expression"
    echo "  -v               # Verbose output"
    echo "  -q               # Quiet output"
    echo "  -x               # Stop after first failure"
    echo "  --maxfail=N      # Stop after N failures"
    echo "  --tb=short       # Short traceback format"
    echo "  --disable-warnings # Disable warning summary"
    echo ""
    exit 0
fi

echo "🔗 Running Integration Tests (Database Required)"
echo "==============================================="

# These tests always need containers - never run without them
echo "🐳 Integration tests require Docker containers for database access"
export ENVIRONMENT=test

# Display what tests will be run
if [[ -n "$PYTEST_ARGS" ]]; then
    echo "📋 Running with parameters: $PYTEST_ARGS"
fi

# Function to check if containers are running and healthy
check_containers() {
    echo "🔍 Checking container status..."
    
    # Check if docker compose is available
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is not installed or not in PATH"
        return 1
    fi
    
    # Check if containers are running (without jq dependency)
    local running_containers=$(docker compose ps --status running --format "table {{.Service}}\t{{.Status}}" | grep -v "SERVICE" | wc -l)
    
    if [ "$running_containers" -lt 1 ]; then
        echo "⚠️  No containers currently running"
        return 1
    fi
    
    # Check specific services
    local web_running=$(docker compose ps web --status running -q | wc -l)
    local db_running=$(docker compose ps postgres --status running -q | wc -l)
    
    echo "   Web container running: $([ $web_running -gt 0 ] && echo 'yes' || echo 'no')"
    echo "   Database container running: $([ $db_running -gt 0 ] && echo 'yes' || echo 'no')"
    
    if [ "$web_running" -lt 1 ] || [ "$db_running" -lt 1 ]; then
        echo "❌ Required containers are not running"
        return 1
    fi
    
    echo "✅ All required containers are running"
    return 0
}
# Function to start containers and run tests
start_containers_and_run_tests() {
    echo "🚀 Starting Docker services..."
    if ! docker compose up -d; then
        echo "❌ Failed to start Docker containers"
        exit 1
    fi
    
    # Wait for services to be ready with better health checking
    echo "⏳ Waiting for services to be ready..."
    local max_attempts=60  # 2 minutes
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if check_containers; then
            # Additional check: try to connect to the web service
            if docker compose exec -T web python -c "
import requests
import sys
try:
    response = requests.get('http://localhost:5000/', timeout=5)
    print('✅ Web service is responding')
    sys.exit(0)
except Exception as e:
    print(f'Web service not ready: {e}')
    sys.exit(1)
" 2>/dev/null; then
                echo "✅ All services are ready!"
                break
            fi
        fi
        
        if [ $((attempt % 15)) -eq 0 ]; then
            echo "   Still waiting for services (attempt $attempt/$max_attempts)..."
        fi
        
        sleep 2
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        echo "❌ Services failed to become ready within expected time"
        echo "📋 Container status:"
        docker compose ps
        echo "📋 Container logs:"
        docker compose logs --tail=20
        exit 1
    fi
    
    # Run integration tests inside container
    echo "🔍 Running Integration Tests in Docker..."
    if ! docker compose exec -T web bash -c "
        cd /app &&
        python -m pytest tests/integration/ -v --tb=short $PYTEST_ARGS
    "; then
        echo "❌ Integration tests failed"
        echo "📋 Recent logs from web container:"
        docker compose logs --tail=50 web
        exit 1
    fi
}

# Function to cleanup containers
cleanup_containers() {
    echo "� Stopping Docker services..."
    docker compose down || echo "⚠️  Some containers may have already been stopped"
}

# Main execution - always use containers
echo "🔍 Checking if containers are already running..."

if check_containers; then
    echo "✅ Containers are already running, running tests directly"
    # Run integration tests inside existing container
    echo "🔍 Running Integration Tests in existing Docker containers..."
    if ! docker compose exec -T web bash -c "
        cd /app &&
        python -m pytest tests/integration/ -v --tb=short $PYTEST_ARGS
    "; then
        echo "❌ Integration tests failed"
        exit 1
    fi
else
    echo "🚀 Need to start containers first"
    start_containers_and_run_tests
    cleanup_containers
fi

echo -e "\n✅ Integration Tests Complete!"
echo "These tests verify system integration with real database connections."
