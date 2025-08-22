# Testing Guide

This document explains how to run the comprehensive test suite for the Budget App.

## Test Types

### 🔬 Integration Tests
- **Purpose**: Test the complete application stack with real database
- **Database**: Separate test database (`budget_test_db` on port 5433)
- **Coverage**: Authentication, all pages, API endpoints, data operations
- **Location**: `tests/test_integration.py`

### 🧪 Unit Tests  
- **Purpose**: Test individual components and logic
- **Database**: Local or mocked
- **Coverage**: Business logic, database operations
- **Location**: `src/test_logic.py`, `tests/test_import_cli.py`

## Running Tests

### Integration Tests (Recommended)
```bash
# Run comprehensive integration tests
make test-integration

# Or run directly
./run_integration_tests.sh
```

This will:
1. Start separate test containers (PostgreSQL + Web App)
2. Run all integration tests
3. Generate HTML report (`test-report.html`)
4. Clean up test containers automatically

### Unit Tests
```bash
# Run unit tests
make test-unit

# Or run specific tests
make install-dev  # Install dev environment first
source venv/bin/activate
cd src && python -m pytest test_logic.py -v
```

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
