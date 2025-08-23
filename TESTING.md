# Test Guide for Budget App

This document describes the test structure and how to run tests for the Budget App.

## 📁 Test Organization

All tests have been moved to the `tests/` directory for better organization:

```
tests/
├── __init__.py              # Makes tests directory a Python package
├── conftest.py              # Pytest configuration and fixtures
├── test_db_connection.py    # Database connection verification
├── test_import_cli.py       # CSV import CLI functionality tests  
├── test_integration.py      # Full integration tests with Docker
├── test_integration_simple.py # Simple integration tests
├── test_logic.py            # Business logic unit tests
└── test_logic_postgres.py  # PostgreSQL-specific logic tests
```

## 🚀 Running Tests

### Quick Test Check

Use the test runner for a quick overview:
```bash
python test_runner.py
```

### Docker-based Testing (Recommended)

1. **Start test environment:**
   ```bash
   docker-compose -f docker-compose.test.yml up -d
   ```

2. **Run tests inside container:**
   ```bash
   docker exec -it budget_web_test bash -c "
   export POSTGRES_HOST=postgres-test
   export POSTGRES_USER=budget_test_user  
   export POSTGRES_PASSWORD=budget_test_password
   export POSTGRES_PORT=5432
   cd /app && python -m pytest tests/ -v
   "
   ```

3. **Clean up:**
   ```bash
   docker-compose -f docker-compose.test.yml down -v
   ```

### Local Testing

For local testing, ensure PostgreSQL is running and environment variables are set:

```bash
# Set test database variables
export POSTGRES_HOST=localhost
export POSTGRES_DB=budget_test_db  
export POSTGRES_USER=budget_test_user
export POSTGRES_PASSWORD=budget_test_password
export POSTGRES_PORT=5433

# Run tests
python -m pytest tests/ -v
```

## 🧪 Test Types

### Unit Tests
- **`test_logic.py`** - Business logic unit tests
- **`test_logic_postgres.py`** - PostgreSQL-specific tests
- **`test_import_cli.py`** - CSV import functionality

### Integration Tests  
- **`test_integration.py`** - Full integration tests with web server
- **`test_integration_simple.py`** - Simple web app structure tests
- **`test_db_connection.py`** - Database connectivity verification

## 📋 Test Categories

### ✅ Working Tests
- Database connection tests
- Basic business logic tests  
- Module import tests
- Test organization verification

### ⚠️ Tests Needing Updates
- Some PostgreSQL-specific tests need better test isolation
- Integration tests may need Docker setup modifications
- Legacy SQLite-based tests need PostgreSQL migration

## 🛠️ Test Configuration

### Environment Variables
Tests use these environment variables (see `conftest.py`):

```bash
POSTGRES_HOST=localhost          # Database host
POSTGRES_DB=budget_test_db       # Test database name  
POSTGRES_USER=budget_test_user   # Database user
POSTGRES_PASSWORD=budget_test_password # Database password
POSTGRES_PORT=5433               # Test database port
```

### Test Database Setup

The test database should be separate from the main application database:

1. **Using Docker:** `docker-compose.test.yml` provides isolated test database
2. **Manual Setup:** Create dedicated test database with test user credentials

## 🔧 Pytest Configuration

The `conftest.py` file provides:
- Automatic `src/` directory inclusion in Python path
- Environment variable configuration
- Common test fixtures (can be extended)

## 📊 Running Specific Tests

```bash
# Run all unit tests
python -m pytest tests/test_logic.py -v

# Run specific test
python -m pytest tests/test_logic.py::TestBudgetLogic::test_db_connection -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run integration tests only
python -m pytest tests/test_integration* -v
```

## 🚫 Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL test database is running
- Check environment variables match database configuration  
- Verify test database credentials and permissions

### Import Errors
- Tests automatically add `src/` to Python path via `conftest.py`
- Ensure all dependencies are installed (`pip install -r src/requirements.txt`)

### Test Isolation Issues
- Some tests may need better cleanup between runs
- Consider using test-specific database schemas or transactions

## 🎯 Future Improvements

1. **Better Test Isolation:** Implement transaction rollback between tests
2. **Mock Objects:** Add mocking for external dependencies
3. **Performance Tests:** Add load testing for critical functionality  
4. **CI/CD Integration:** Set up automated testing pipeline
5. **Code Coverage:** Improve test coverage reporting

This test structure provides a solid foundation for maintaining and expanding the Budget App's test suite! 🧪✨

## Test Database

The integration tests use a completely separate database to avoid conflicts:

| Environment | Database | Port | User | Purpose |
|-------------|----------|------|------|---------|
| **Development** | `budget_db` | 5432 | `budget_user` | Main application |
| **Testing** | `budget_test_db` | 5433 | `budget_test_user` | Integration tests |

## Test Configuration

### Environment Files
- `.env` - Main application configuration
- `.env.test` - Test-specific configuration
- `docker-compose.yml` - Main application stack
- `docker-compose.test.yml` - Test stack with separate database

### Test Credentials
- **Username**: `admin`
- **Password**: `admin`
- **Base URL**: `http://localhost:5001` (test server)

## Test Coverage

### ✅ Currently Tested
- **Authentication**: Login, logout, session management, route protection
- **Page Access**: All pages load correctly (dashboard, transactions, budgets, reports, import, uncategorized)
- **API Endpoints**: Categories, transactions, uncategorized, budgets, reports
- **Database Integration**: Connection, data persistence, CRUD operations

### 🔄 Areas for Improvement
- CSV import functionality
- Budget CRUD operations
- Auto-classification features
- Error handling edge cases

## Test Results

Last test run: **18/22 tests passing (82% success rate)**

View detailed results in `test-report.html` after running integration tests.

## CI/CD Integration

To integrate with CI/CD pipelines:

```bash
# In your CI script
./run_integration_tests.sh
```

The script returns appropriate exit codes:
- `0` - All tests passed
- `1` - Some tests failed

## Troubleshooting

### Common Issues

1. **Port conflicts**: 
   - Tests use port 5433 for database, 5001 for web app
   - Stop main application if needed: `make down`

2. **Docker not running**:
   - Ensure Docker is started and accessible
   - Check: `docker info`

3. **Tests hanging**:
   - Use timeout: `timeout 300 ./run_integration_tests.sh`
   - Check container logs: `docker compose -f docker-compose.test.yml logs`

4. **Test database issues**:
   - Clean up: `docker compose -f docker-compose.test.yml down -v`
   - Check database connectivity on port 5433

### Manual Testing

If automated tests fail, you can manually test:

```bash
# Start test stack
docker compose -f docker-compose.test.yml up -d

# Test login
curl -X POST -d "username=admin&password=admin" http://localhost:5001/login

# Test API
curl -b cookies.txt http://localhost:5001/api/categories

# Cleanup
docker compose -f docker-compose.test.yml down -v
```

## Contributing

When adding new features:

1. Add corresponding integration tests to `tests/test_integration.py`
2. Update unit tests in `src/test_logic.py`
3. Run full test suite before committing
4. Update this documentation if needed

## Performance

Integration test suite takes approximately **2-3 minutes** to run:
- Container startup: ~30-60 seconds
- Test execution: ~90-120 seconds  
- Cleanup: ~10 seconds

For faster development cycles, use unit tests during development and integration tests before commits.
