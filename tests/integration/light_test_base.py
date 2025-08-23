"""
Light Integration Test Base for Web Service Testing

A minimal, fast integration test base that avoids the complex setup
that causes hanging issues in RobustIntegrationTestBase.

Features:
- Fast setup (no complex user management)
- Direct HTTP testing
- Simple container checking
- Reliable service waiting
- Basic authentication helpers
"""

import os
import time
import requests
import pytest
from typing import Optional


def is_running_in_container() -> bool:
    """Check if we're running inside a Docker container"""
    return os.path.exists('/.dockerenv')


def simple_container_check():
    """Simple decorator to ensure we're in container environment"""
    if not is_running_in_container():
        return pytest.mark.skip(reason="Integration tests must run inside Docker containers")
    return lambda x: x


class LightIntegrationTestBase:
    """
    Lightweight integration test base for web service testing
    
    This base class provides:
    - Fast setup without complex database operations
    - Simple service readiness checking
    - Basic HTTP request helpers
    - Minimal authentication support
    
    Use this for tests that primarily test web endpoints and don't need
    complex database user management.
    """
    
    # Test configuration
    BASE_URL = "http://localhost:5000"
    REQUEST_TIMEOUT = 10  # Default timeout for HTTP requests
    
    def setup_method(self, method):
        """Lightweight setup method"""
        print(f"\n⚡ Quick setup: {method.__name__}")
        
        # Wait for web service to be ready
        self._wait_for_web_service()
        
        # Initialize session for HTTP requests
        self.session = requests.Session()
        self.session.timeout = self.REQUEST_TIMEOUT
        
        print("✅ Light setup completed")
    
    def teardown_method(self, method):
        """Cleanup method"""
        if hasattr(self, 'session'):
            self.session.close()
    
    def _wait_for_web_service(self, max_wait: int = 15):
        """Wait for web service to be ready with minimal overhead"""
        print("⏳ Checking web service...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                # Test the login page (most reliable endpoint)
                response = requests.get(f"{self.BASE_URL}/login", timeout=3)
                if response.status_code == 200 and 'login' in response.text.lower():
                    print("✅ Web service ready!")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(1)
        
        print(f"⚠ Web service not ready after {max_wait}s, continuing anyway...")
        return False
    
    def get_request(self, endpoint: str, **kwargs) -> requests.Response:
        """Make a GET request with default timeout"""
        url = f"{self.BASE_URL}{endpoint}"
        kwargs.setdefault('timeout', self.REQUEST_TIMEOUT)
        return self.session.get(url, **kwargs)
    
    def post_request(self, endpoint: str, **kwargs) -> requests.Response:
        """Make a POST request with default timeout"""
        url = f"{self.BASE_URL}{endpoint}"
        kwargs.setdefault('timeout', self.REQUEST_TIMEOUT)
        return self.session.post(url, **kwargs)
    
    def assert_page_loads(self, endpoint: str, expected_content: str = None) -> requests.Response:
        """
        Assert that a page loads successfully
        
        Args:
            endpoint: The endpoint to test (e.g., '/login', '/dashboard')
            expected_content: Optional content to check for in the response
            
        Returns:
            The response object for further assertions
        """
        response = self.get_request(endpoint)
        assert response.status_code == 200, f"Expected 200, got {response.status_code} for {endpoint}"
        
        if expected_content:
            assert expected_content.lower() in response.text.lower(), \
                f"Expected '{expected_content}' in response for {endpoint}"
        
        return response
    
    def login_user(self, username: str, password: str) -> requests.Response:
        """
        Attempt to login a user
        
        Args:
            username: Username to login with
            password: Password to login with
            
        Returns:
            The login response
        """
        login_data = {
            'username': username,
            'password': password
        }
        return self.post_request('/login', data=login_data)
    
    def create_authenticated_session(self, username: str, password: str) -> requests.Session:
        """
        Create a new session and authenticate it
        
        Args:
            username: Username to login with  
            password: Password to login with
            
        Returns:
            Authenticated session
            
        Note: This requires the user to already exist in the database
        """
        session = requests.Session()
        session.timeout = self.REQUEST_TIMEOUT
        
        login_response = session.post(f"{self.BASE_URL}/login", data={
            'username': username,
            'password': password
        }, timeout=self.REQUEST_TIMEOUT)
        
        if login_response.status_code not in [200, 302]:
            raise Exception(f"Authentication failed: {login_response.status_code}")
        
        return session
    
    def assert_requires_authentication(self, endpoint: str):
        """
        Assert that an endpoint requires authentication (redirects to login)
        
        Args:
            endpoint: The protected endpoint to test
        """
        response = self.get_request(endpoint, allow_redirects=False)
        assert response.status_code in [302, 401], \
            f"Expected redirect or unauthorized, got {response.status_code} for protected endpoint {endpoint}"
    
    def assert_json_response(self, endpoint: str, expected_status: int = 200) -> dict:
        """
        Assert that an endpoint returns valid JSON
        
        Args:
            endpoint: The API endpoint to test
            expected_status: Expected HTTP status code
            
        Returns:
            Parsed JSON response
        """
        response = self.get_request(endpoint)
        assert response.status_code == expected_status, \
            f"Expected {expected_status}, got {response.status_code} for {endpoint}"
        
        try:
            return response.json()
        except ValueError as e:
            pytest.fail(f"Invalid JSON response from {endpoint}: {e}")


@simple_container_check()
class LightWebTestBase(LightIntegrationTestBase):
    """
    Container-enforced version of LightIntegrationTestBase
    
    Use this as the base class for integration tests that need to run
    inside Docker containers but want lightweight setup.
    """
    pass


# Example usage and test helpers
class WebServiceTestMixin:
    """Mixin with common web service test patterns"""
    
    def test_health_endpoints_pattern(self):
        """Common pattern for testing health/status endpoints"""
        # Test that basic pages load
        self.assert_page_loads('/login', 'login')
        
        # Test that API endpoints are accessible (even if they return errors)
        health_response = self.get_request('/health')
        assert health_response.status_code in [200, 503], "Health endpoint should respond"
    
    def test_authentication_pattern(self):
        """Common pattern for testing authentication flows"""
        # Test login page loads
        self.assert_page_loads('/login', 'username')
        
        # Test that protected endpoints require auth
        self.assert_requires_authentication('/transactions')
        self.assert_requires_authentication('/budgets')
        self.assert_requires_authentication('/reports')
    
    def test_api_endpoints_pattern(self):
        """Common pattern for testing API endpoints availability"""
        api_endpoints = [
            '/api/categories',
            '/api/transactions', 
            '/api/uncategorized'
        ]
        
        for endpoint in api_endpoints:
            response = self.get_request(endpoint)
            # API endpoints should either work (200) or require auth (401/302)
            assert response.status_code in [200, 302, 401], \
                f"API endpoint {endpoint} should respond properly"


# Convenience functions for quick testing
def quick_web_test(endpoint: str, expected_content: str = None) -> bool:
    """
    Quick function to test if a web endpoint is working
    
    Args:
        endpoint: Endpoint to test
        expected_content: Optional content to look for
        
    Returns:
        True if test passes, False otherwise
    """
    try:
        base_url = "http://localhost:5000"
        response = requests.get(f"{base_url}{endpoint}", timeout=5)
        
        if response.status_code != 200:
            return False
        
        if expected_content and expected_content.lower() not in response.text.lower():
            return False
        
        return True
    except:
        return False


def quick_service_check() -> dict:
    """
    Quick service health check
    
    Returns:
        Dictionary with service status information
    """
    results = {}
    base_url = "http://localhost:5000"
    
    endpoints = {
        'login': '/login',
        'health': '/health',
        'api_categories': '/api/categories'
    }
    
    for name, endpoint in endpoints.items():
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=3)
            results[name] = {
                'status': response.status_code,
                'response_time': response.elapsed.total_seconds(),
                'accessible': response.status_code < 500
            }
        except Exception as e:
            results[name] = {
                'status': 'error',
                'error': str(e),
                'accessible': False
            }
    
    return results
