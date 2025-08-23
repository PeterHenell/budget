#!/bin/bash

# Function to check if containers are running
check_containers() {
    if docker compose exec -T web bash -c "
        cd /app &&
        python -c 'import sys; sys.exit(0)'
    " 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to start containers and run tests
start_containers_and_run_tests() {
    echo "🚀 Starting Docker containers for integration testing..."
    docker compose up -d
    
    # Wait for services to be ready
    echo "⏳ Waiting for services to start..."
    sleep 10
    
    # Check if containers are running
    if ! check_containers; then
        echo "❌ Failed to start containers"
        exit 1
    fi
    
    # Initialize database for integration tests
    echo "🔧 Initializing database..."
    docker compose exec -T web bash -c "cd /app && python init_database.py --skip-admin" || true
    
    # Run integration tests
    echo "🔍 Running Integration Tests..."
    if ! docker compose exec -T web bash -c "
        cd /app &&
        python -m pytest tests/integration/ -v --tb=short $PYTEST_ARGS
    "; then
        echo "❌ Integration tests failed"
        exit 1
    fi
}

# Function to cleanup containers
cleanup_containers() {
    echo "🧹 Stopping Docker services..."
    docker compose down || echo "⚠️  Some containers may have already been stopped"
}

# Parse command line arguments for pytest
PYTEST_ARGS="$@"

# Main execution
echo "🔍 Checking if containers are already running..."

if check_containers; then
    echo "✅ Containers are already running, running tests directly"
    
    # Initialize database schema for integration tests
    echo "🔧 Initializing database schema..."
    if docker compose exec -T web bash -c "
        cd /app &&
        python init_database.py --skip-admin 2>/dev/null
    "; then
        echo "✅ Database schema initialized successfully"
    else
        echo "⚠️ Database initialization had issues, but continuing (may already be initialized)"
    fi
    
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
