"""
Pytest configuration for Budget App tests
"""
import sys
import os
from pathlib import Path

# Add the src directory to Python path so all tests can import modules
src_dir = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_dir))

# Set test environment variables
# When running in Docker, use the postgres service, otherwise localhost for local testing
postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
postgres_port = os.getenv('POSTGRES_PORT', '5432')

# Check if we're running in the Docker environment
if postgres_host == 'postgres':
    # Running in Docker container
    os.environ['POSTGRES_HOST'] = 'postgres'
    os.environ['POSTGRES_DB'] = os.getenv('POSTGRES_DB', 'budget_db')
    os.environ['POSTGRES_USER'] = os.getenv('POSTGRES_USER', 'budget_user')
    os.environ['POSTGRES_PASSWORD'] = os.getenv('POSTGRES_PASSWORD', 'budget_password_2025')
    os.environ['POSTGRES_PORT'] = '5432'
else:
    # Running locally - use test database settings
    os.environ['POSTGRES_HOST'] = 'localhost'
    os.environ['POSTGRES_DB'] = os.getenv('POSTGRES_TEST_DB', 'budget_test_db')
    os.environ['POSTGRES_USER'] = os.getenv('POSTGRES_USER', 'budget_test_user')
    os.environ['POSTGRES_PASSWORD'] = os.getenv('POSTGRES_PASSWORD', 'budget_test_password')
    os.environ['POSTGRES_PORT'] = os.getenv('POSTGRES_PORT', '5433')
