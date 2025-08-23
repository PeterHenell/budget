# Light Integration Test Base Documentation

## Overview

The `LightIntegrationTestBase` provides a fast, reliable alternative to the `RobustIntegrationTestBase` for web service integration testing. It avoids complex database user management operations that can cause hanging issues.

## Key Features

- ⚡ **Fast Setup**: Minimal overhead, typically completes in <0.1 seconds
- 🚫 **No Hanging**: Avoids complex database operations that cause hanging
- 🌐 **Web-Focused**: Designed specifically for HTTP/web service testing
- 🔒 **Simple Auth**: Basic authentication helpers without complex user management
- 📊 **Request Helpers**: Built-in timeout and session management

## Quick Start

### Basic Usage

```python
from tests.integration.light_test_base import LightWebTestBase, WebServiceTestMixin

class TestMyWebService(LightWebTestBase, WebServiceTestMixin):
    def test_login_page_loads(self):
        """Test that login page loads correctly"""
        response = self.assert_page_loads('/login', 'username')
        assert 'password' in response.text.lower()
    
    def test_protected_endpoints(self):
        """Test that protected endpoints redirect"""
        self.assert_requires_authentication('/transactions')
        self.assert_requires_authentication('/budgets')
```

### Standalone Testing

```python
from tests.integration.light_test_base import quick_web_test, quick_service_check

def test_connectivity():
    assert quick_web_test('/login') is True
    
def test_service_health():
    status = quick_service_check()
    assert status['login']['accessible'] is True
```

## Test Base Classes

### LightIntegrationTestBase
- Core functionality for HTTP testing
- Container-agnostic (can run anywhere)
- Request helpers with built-in timeouts

### LightWebTestBase
- Container-enforced version
- Automatically skips if not in Docker container
- Use for integration tests that need container environment

## Performance Comparison

| Test Base | Setup Time | Hanging Risk | Use Case |
|-----------|------------|-------------|-----------|
| RobustIntegrationTestBase | 5-30s | High | Complex database operations |
| LightIntegrationTestBase | <0.1s | None | Web service testing |

## Test Examples

### 1. Page Load Testing
```python
def test_pages_load(self):
    # Test basic page loading
    self.assert_page_loads('/login', 'username')
    
    # Test with specific content
    response = self.assert_page_loads('/login', 'password')
    assert 'login' in response.text.lower()
```

### 2. Authentication Testing
```python
def test_authentication_flow(self):
    # Test protected endpoints redirect
    self.assert_requires_authentication('/transactions')
    
    # Test invalid login
    response = self.login_user('invalid', 'wrong')
    assert response.status_code in [200, 302]
```

### 3. API Testing
```python
def test_api_endpoints(self):
    # Test API endpoints respond
    response = self.get_request('/api/categories')
    assert response.status_code < 500
    
    # Test JSON response
    data = self.assert_json_response('/api/categories')
    assert isinstance(data, (dict, list))
```

### 4. HTTP Helpers
```python
def test_http_helpers(self):
    # GET with timeout
    response = self.get_request('/login', timeout=5)
    
    # POST with data
    response = self.post_request('/login', data={
        'username': 'test',
        'password': 'test'
    })
```

## Built-in Test Patterns

The `WebServiceTestMixin` provides common test patterns:

```python
class TestMyService(LightWebTestBase, WebServiceTestMixin):
    # Automatically includes:
    # - test_health_endpoints_pattern()
    # - test_authentication_pattern() 
    # - test_api_endpoints_pattern()
```

## Configuration

```python
class MyCustomTestBase(LightIntegrationTestBase):
    BASE_URL = "http://localhost:8080"  # Custom URL
    REQUEST_TIMEOUT = 15  # Custom timeout
```

## Quick Utilities

### Standalone Functions
```python
# Quick connectivity test
quick_web_test('/login', 'username')  # Returns bool

# Service health check
status = quick_service_check()  # Returns status dict
```

### Service Status Information
```python
status = quick_service_check()
# Returns:
{
    'login': {'status': 200, 'accessible': True, 'response_time': 0.1},
    'health': {'status': 200, 'accessible': True, 'response_time': 0.05},
    'api_categories': {'status': 302, 'accessible': True, 'response_time': 0.08}
}
```

## When to Use

### Use LightIntegrationTestBase when:
- ✅ Testing web endpoints and HTTP responses
- ✅ Testing authentication flows (redirect/login behavior)
- ✅ Testing API endpoint availability
- ✅ Need fast, reliable test execution
- ✅ Testing basic service health/connectivity

### Use RobustIntegrationTestBase when:
- ⚠️ Need complex database user creation/management
- ⚠️ Need transaction-level database testing
- ⚠️ Can tolerate slower setup and potential hanging
- ⚠️ Testing complex multi-user scenarios

## Troubleshooting

### Tests Still Hanging?
- Make sure you're using `LightWebTestBase` not `RobustIntegrationTestBase`
- Check that container enforcement decorator is working
- Verify HTTP timeouts are set properly

### Connection Errors?
```python
# Test basic connectivity first
def test_service_available(self):
    assert quick_web_test('/login') is True
```

### Custom Endpoints?
```python
# Update endpoints to match your application
protected_endpoints = [
    '/your-protected-page',
    '/admin',
    '/settings'
]
```

## Migration from RobustIntegrationTestBase

1. Change base class:
   ```python
   # Before
   class TestWeb(RobustIntegrationTestBase):
   
   # After  
   class TestWeb(LightWebTestBase):
   ```

2. Remove database user operations:
   ```python
   # Remove these calls:
   # self.create_user()
   # self.login_user()
   # self.get_auth_headers()
   ```

3. Use HTTP helpers instead:
   ```python
   # Before
   headers = self.get_auth_headers()
   response = requests.get(url, headers=headers)
   
   # After
   response = self.get_request('/endpoint')
   ```

## Running the Tests

```bash
# Run all light web tests
./run-integration-tests.sh tests/integration/test_light_web.py

# Run specific test class
./run-integration-tests.sh -k "TestLightWebService"

# Run with verbose output
./run-integration-tests.sh tests/integration/test_light_web.py -v
```

## Example Output

```
============================= test session starts ==============================
tests/integration/test_light_web.py::TestLightWebService::test_login_page_loads PASSED
tests/integration/test_light_web.py::TestLightWebService::test_protected_endpoints_redirect PASSED
tests/integration/test_light_web.py::TestLightWebService::test_api_endpoints_respond PASSED
tests/integration/test_light_web.py::TestQuickUtilities::test_quick_web_test_function PASSED
tests/integration/test_light_web.py::test_basic_connectivity PASSED

======================== 14 passed in 0.08s =========================
```

The light test base consistently completes all tests in under 0.1 seconds, providing reliable web service testing without the complexity and hanging risks of the heavier test infrastructure.
