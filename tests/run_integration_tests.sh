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
    if [[ "$COMPOSE_FILE" == "../docker-compose.yml" ]]; then
        cd .. && docker compose down >/dev/null 2>&1 || true
    else
        docker compose -f docker-compose.test.yml down -v --remove-orphans >/dev/null 2>&1 || true
    fi
}

# Function to check if containers are healthy
check_container_health() {
    local max_attempts=120  # Increased to 4 minutes for health checks
    local attempt=1
    local compose_cmd
    
    if [[ "$COMPOSE_FILE" == "../docker-compose.yml" ]]; then
        compose_cmd="cd .. && docker compose"
    else
        compose_cmd="docker compose -f docker-compose.test.yml"
    fi
    
    log_info "Waiting for containers to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        # For test environment, check health status specifically
        if [[ "$COMPOSE_FILE" != "../docker-compose.yml" ]]; then
            local unhealthy_count=$(eval "$compose_cmd ps" | grep -c "unhealthy\|starting" || echo 0)
            local healthy_count=$(eval "$compose_cmd ps" | grep -c "healthy" || echo 0)
            
            # Check if all services have health checks and are healthy
            if [ $healthy_count -ge 2 ] && [ $unhealthy_count -eq 0 ]; then
                log_success "All containers are healthy!"
                return 0
            fi
            
            if [ $((attempt % 15)) -eq 0 ]; then
                log_info "Health status - Healthy: $healthy_count, Unhealthy/Starting: $unhealthy_count (attempt $attempt/$max_attempts)"
            fi
        else
            # For main docker-compose, check if containers are running and web is responsive
            local failed_containers=$(eval "$compose_cmd ps" | grep -v "Up" | grep -v "Name" | grep -v "^$" | wc -l)
            
            if [ $failed_containers -eq 0 ]; then
                # Double-check by trying a simple command in the web container
                if eval "cd .. && docker compose exec -T web echo 'Container ready'" >/dev/null 2>&1; then
                    log_success "All containers are ready!"
                    return 0
                fi
            fi
            
            if [ $((attempt % 15)) -eq 0 ]; then
                log_info "Still waiting for containers to be ready (attempt $attempt/$max_attempts)..."
            fi
        fi
        
        sleep 2
        ((attempt++))
    done
    
    log_error "Containers failed to become ready within expected time"
    return 1
}

# Function to show container logs on failure
show_container_logs() {
    log_error "Container startup failed. Showing logs:"
    echo ""
    
    local compose_cmd
    if [[ "$COMPOSE_FILE" == "../docker-compose.yml" ]]; then
        compose_cmd="cd .. && docker compose"
        # Get service names from main docker-compose
        local containers=$(cd .. && docker compose config --services)
    else
        compose_cmd="docker compose -f docker-compose.test.yml"
        local containers=$(docker compose -f docker-compose.test.yml config --services)
    fi
    
    for container in $containers; do
        echo -e "${YELLOW}=== Logs for $container ===${NC}"
        eval "$compose_cmd logs --tail=50 \"$container\"" 2>/dev/null || {
            log_warning "Could not retrieve logs for $container"
        }
        echo ""
    done
    
    # Also show container status
    echo -e "${YELLOW}=== Container Status ===${NC}"
    eval "$compose_cmd ps"
}

# Set up cleanup trap
trap cleanup EXIT

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if required files exist
COMPOSE_FILE="docker-compose.test.yml"
if [[ ! -f "$COMPOSE_FILE" ]]; then
    log_warning "docker-compose.test.yml not found, checking for main docker-compose.yml"
    cd ..
    if [[ -f "docker-compose.yml" ]]; then
        COMPOSE_FILE="../docker-compose.yml"
        log_info "Using main docker-compose.yml for integration tests"
    else
        log_error "No docker-compose configuration found"
        exit 1
    fi
fi

if [[ ! -d "integration" ]]; then
    log_error "integration test directory not found"
    exit 1
fi

# Install test dependencies locally if needed
if [[ ! -d "../venv" ]]; then
    log_info "Creating virtual environment for test dependencies..."
    cd .. && python3 -m venv venv && cd tests
fi

log_info "Installing/updating test dependencies..."
source ../venv/bin/activate
pip install -q requests pytest pytest-html

# Clean up any existing test containers
log_info "Cleaning up any existing containers..."
if [[ "$COMPOSE_FILE" == "../docker-compose.yml" ]]; then
    cd .. && docker compose down >/dev/null 2>&1 || true
else
    docker compose -f docker-compose.test.yml down -v --remove-orphans >/dev/null 2>&1 || true
fi

# Start the containers
log_info "Starting Docker containers for integration tests..."
if [[ "$COMPOSE_FILE" == "../docker-compose.yml" ]]; then
    if ! (cd .. && docker compose up -d --build); then
        log_error "Failed to start Docker containers"
        show_container_logs
        exit 1
    fi
else
    if ! docker compose -f docker-compose.test.yml up -d --build; then
        log_error "Failed to start Docker containers"
        show_container_logs
        exit 1
    fi
fi

# Wait for containers to be ready
if ! check_container_health; then
    log_error "Containers are not ready. Cannot proceed with tests."
    show_container_logs
    exit 1
fi

# Run integration tests
log_info "Starting integration tests..."
echo ""

# Change to directory containing the test file
cd "$(dirname "$0")"

# Determine test execution method
if [[ "$COMPOSE_FILE" == "../docker-compose.yml" ]]; then
    # Run tests inside the Docker container (like the main integration test runner)
    log_info "Running tests inside Docker container..."
    cd .. && docker compose exec web python -m pytest /app/tests/integration/ \
        -v \
        --tb=short \
        --html=/app/tests/test-report.html \
        --self-contained-html \
        --color=yes
else
    # Run pytest with detailed output locally against test containers
    python -m pytest integration/ \
        -v \
        --tb=short \
        --html=test-report.html \
        --self-contained-html \
        --color=yes
fi

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
