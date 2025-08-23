#!/bin/bash

# start-web.sh - Flask Web Application Startup Script
# Handles initialization and startup of the Budget Flask web application

set -e  # Exit on error

echo "🚀 Starting Budget Web Application"
echo "=================================="

# Environment setup
export FLASK_APP=${FLASK_APP:-web_app.py}
export FLASK_ENV=${FLASK_ENV:-production}
export FLASK_RUN_HOST=${FLASK_RUN_HOST:-0.0.0.0}
export FLASK_RUN_PORT=${FLASK_RUN_PORT:-5000}

# Database connection parameters (can be overridden by environment)
export DB_HOST=${DB_HOST:-postgres}
export DB_PORT=${DB_PORT:-5432}
export DB_NAME=${DB_NAME:-budget_db}
export DB_USER=${DB_USER:-budget_user}
export DB_PASSWORD=${DB_PASSWORD:-budget_password_2025}

echo "ℹ️  Configuration:"
echo "   Flask App: $FLASK_APP"
echo "   Environment: $FLASK_ENV"
echo "   Host: $FLASK_RUN_HOST:$FLASK_RUN_PORT"
echo "   Database: $DB_HOST:$DB_PORT/$DB_NAME"

# Wait for database to be ready
echo "⏳ Waiting for database connection..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if python -c "
import psycopg2
import sys
try:
    conn = psycopg2.connect(
        host='$DB_HOST',
        port=$DB_PORT,
        database='$DB_NAME',
        user='$DB_USER',
        password='$DB_PASSWORD'
    )
    conn.close()
    print('✅ Database connection successful')
    sys.exit(0)
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
        break
    fi
    
    echo "   Database not ready (attempt $attempt/$max_attempts)..."
    sleep 2
    ((attempt++))
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ Database connection failed after $max_attempts attempts"
    exit 1
fi

# Check if database needs initialization
echo "🔍 Checking database initialization..."
if python -c "
import psycopg2
import sys
try:
    conn = psycopg2.connect(
        host='$DB_HOST',
        port=$DB_PORT,
        database='$DB_NAME',
        user='$DB_USER',
        password='$DB_PASSWORD'
    )
    cursor = conn.cursor()
    cursor.execute(\"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'users'\")
    count = cursor.fetchone()[0]
    conn.close()
    if count == 0:
        print('Database needs initialization')
        sys.exit(1)
    else:
        print('Database already initialized')
        sys.exit(0)
except Exception as e:
    print(f'Error checking database: {e}')
    sys.exit(1)
"; then
    echo "✅ Database is initialized"
else
    echo "🔧 Initializing database..."
    if [ -f "init_database.py" ]; then
        python init_database.py
        echo "✅ Database initialization completed"
    else
        echo "⚠️  init_database.py not found, skipping database initialization"
    fi
fi

# Python syntax check
echo "🔍 Checking Python syntax..."
if python -m py_compile "$FLASK_APP"; then
    echo "✅ Syntax check passed"
else
    echo "❌ Syntax check failed"
    exit 1
fi

# Create uploads directory if it doesn't exist
mkdir -p uploads
echo "✅ Uploads directory ready"

# Start the Flask application
echo "🚀 Starting Flask application..."

if [ "$FLASK_ENV" = "development" ]; then
    echo "🔧 Running in development mode with auto-reload"
    exec python -m flask run --debug --reload
else
    echo "🏭 Running in production mode"
    exec python "$FLASK_APP"
fi
