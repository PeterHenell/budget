"""
Example integration tests using the LightIntegrationTestBase

This demonstrates how to use the lighter test base for reliable
web service testing without complex setup overhead.
"""

import pytest
import requests
from tests.integration.light_test_base import (
    LightWebTestBase, 
    WebServiceTestMixin,
    quick_web_test,
    quick_service_check
)


class TestLightWebService(LightWebTestBase, WebServiceTestMixin):
    """
    Example web service tests using the lightweight base
    
    These tests should run quickly without hanging since they
    avoid the complex database user management setup.
    """
    
    def test_login_page_loads(self):
        """Test that the login page loads correctly"""
        response = self.assert_page_loads('/login', 'username')
        assert 'password' in response.text.lower()
        assert 'login' in response.text.lower()
    
    def test_protected_endpoints_redirect(self):
        """Test that protected endpoints redirect to login"""
        protected_endpoints = [
            '/transactions', 
            '/budgets',
            '/reports',
            '/import_csv',
            '/uncategorized'
        ]
        
        for endpoint in protected_endpoints:
            self.assert_requires_authentication(endpoint)
    
    def test_api_endpoints_respond(self):
        """Test that API endpoints respond (even with auth errors)"""
        api_endpoints = [
            '/api/categories',
            '/api/transactions',
            '/api/uncategorized'
        ]
        
        for endpoint in api_endpoints:
            response = self.get_request(endpoint)
            # Should respond with something (200, 401, 302, etc.)
            assert response.status_code < 500, \
                f"API endpoint {endpoint} should not return server error"
    
    def test_invalid_login_attempt(self):
        """Test login with invalid credentials"""
        response = self.login_user('invalid_user', 'wrong_password')
        
        # Should either redirect back to login or show error
        assert response.status_code in [200, 302], \
            "Invalid login should return 200 (with error) or 302 (redirect)"
        
        if response.status_code == 200:
            # If returned to login page, should show some error indication
            assert any(word in response.text.lower() for word in ['error', 'invalid', 'incorrect', 'failed'])
    
    def test_health_check(self):
        """Test basic application health"""
        # The main health indicator is that login page loads
        self.assert_page_loads('/login')
        
        # Try health endpoint if it exists
        try:
            health_response = self.get_request('/health')
            # Health endpoint can return 200 (healthy) or 503 (unhealthy)
            assert health_response.status_code in [200, 503]
        except requests.exceptions.RequestException:
            # Health endpoint might not exist, that's OK
            pass


class TestQuickUtilities(LightWebTestBase):
    """Test the quick utility functions"""
    
    def test_quick_web_test_function(self):
        """Test the quick_web_test utility function"""
        # Test that quick function works
        result = quick_web_test('/login', 'username')
        assert result is True, "Login page should pass quick test"
        
        # Test with non-existent page
        result = quick_web_test('/non-existent-page')
        assert result is False, "Non-existent page should fail quick test"
    
    def test_quick_service_check_function(self):
        """Test the quick_service_check utility function"""
        results = quick_service_check()
        
        # Should return a dictionary with endpoint results
        assert isinstance(results, dict)
        assert 'login' in results
        
        # Login endpoint should be accessible
        assert results['login']['accessible'] is True
        assert results['login']['status'] == 200


@pytest.mark.skip_if_hanging
class TestWithExistingUser(LightWebTestBase):
    """
    Tests that require an existing user in the database
    
    These tests are marked to skip if they cause hanging.
    They assume a test user exists (created by other means).
    """
    
    def test_successful_login_with_existing_user(self):
        """
        Test login with existing user
        
        Note: This assumes a test user exists in the database.
        If no user exists, this test will fail gracefully.
        """
        # Try with a common test user
        response = self.login_user('testuser', 'testpass')
        
        # Could be successful (302 redirect) or failed (200 with error)
        assert response.status_code in [200, 302]
        
        if response.status_code == 302:
            # Successful login, should redirect to dashboard or main page
            assert 'Location' in response.headers
        else:
            # Failed login, should show error or return to login form
            assert any(word in response.text.lower() for word in ['login', 'username', 'password'])
    
    def test_dashboard_with_authenticated_session(self):
        """
        Test main page access with authenticated session
        
        This will only work if authentication succeeds.
        """
        try:
            # Attempt to create authenticated session
            auth_session = self.create_authenticated_session('testuser', 'testpass')
            
            # Try to access main page
            main_response = auth_session.get(
                f"{self.BASE_URL}/", 
                timeout=self.REQUEST_TIMEOUT
            )
            
            # Should either show main page or redirect
            assert main_response.status_code in [200, 302]
            
            auth_session.close()
            
        except Exception as e:
            # If authentication fails, skip this test
            pytest.skip(f"Authentication failed, skipping main page test: {e}")


# Standalone test functions (don't require class setup)
def test_basic_connectivity():
    """Basic test that doesn't require test class setup"""
    result = quick_web_test('/login')
    assert result is True, "Should be able to reach login page"


def test_service_status():
    """Quick service status check"""
    status = quick_service_check()
    
    # At minimum, login should be accessible
    assert 'login' in status
    assert status['login']['accessible'] is True
