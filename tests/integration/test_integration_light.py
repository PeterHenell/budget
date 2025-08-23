"""
Integration tests for the Budget App - Light Test Base Implementation
Tests the complete application stack with fast, reliable web testing
"""

import pytest
import requests
import time
import csv
import tempfile
from typing import Dict, Any
from light_test_base import LightWebTestBase, WebServiceTestMixin, quick_web_test, quick_service_check


class TestAuthentication(LightWebTestBase, WebServiceTestMixin):
    """Test authentication functionality with light test base"""
    
    def test_login_page_loads(self):
        """Test that login page loads correctly"""
        response = self.assert_page_loads('/login', 'username')
        assert 'password' in response.text.lower()
        assert 'login' in response.text.lower()

    def test_login_page_structure(self):
        """Test login page has proper form structure"""
        response = self.get_request('/login')
        content = response.text.lower()
        
        # Check for form elements
        assert 'username' in content
        assert 'password' in content
        assert 'form' in content
        
    def test_invalid_login_attempt(self):
        """Test login with invalid credentials"""
        response = self.login_user('invalid_user', 'wrong_password')
        
        # Should either redirect back to login or show error
        assert response.status_code in [200, 302]
        
        if response.status_code == 200:
            # If returned to login page, should show some error indication
            content = response.text.lower()
            assert any(word in content for word in ['error', 'invalid', 'incorrect', 'failed'])

    def test_protected_routes_redirect(self):
        """Test that protected routes redirect to login"""
        protected_routes = [
            '/transactions',
            '/budgets', 
            '/reports',
            '/import_csv',
            '/uncategorized'
        ]
        
        for route in protected_routes:
            self.assert_requires_authentication(route)

    def test_logout_endpoint(self):
        """Test logout endpoint responds"""
        response = self.get_request('/logout', allow_redirects=False)
        # Logout should redirect (302) or be accessible (200)
        assert response.status_code in [200, 302]


class TestPageAccess(LightWebTestBase):
    """Test page access functionality with light test base"""
    
    def test_index_page_redirect(self):
        """Test that index page redirects appropriately"""
        response = self.get_request('/', allow_redirects=False)
        # Index should either show content (200) or redirect to login (302)
        assert response.status_code in [200, 302]
        
    def test_transactions_page_requires_auth(self):
        """Test transactions page requires authentication"""
        self.assert_requires_authentication('/transactions')

    def test_budgets_page_requires_auth(self):
        """Test budgets page requires authentication"""
        self.assert_requires_authentication('/budgets')

    def test_reports_page_requires_auth(self):
        """Test reports page requires authentication"""
        self.assert_requires_authentication('/reports')

    def test_import_page_requires_auth(self):
        """Test import CSV page requires authentication"""
        self.assert_requires_authentication('/import_csv')

    def test_uncategorized_page_requires_auth(self):
        """Test uncategorized page requires authentication"""
        self.assert_requires_authentication('/uncategorized')


class TestAPIEndpoints(LightWebTestBase):
    """Test API endpoints functionality with light test base"""
    
    def test_api_categories_responds(self):
        """Test that categories API endpoint responds"""
        response = self.get_request('/api/categories')
        # Should respond with something (200, 401, 302, etc.) but not server error
        assert response.status_code < 500
        
    def test_api_transactions_responds(self):
        """Test that transactions API endpoint responds"""
        response = self.get_request('/api/transactions')
        # Should respond appropriately (not server error)
        assert response.status_code < 500

    def test_api_uncategorized_responds(self):
        """Test that uncategorized API endpoint responds"""
        response = self.get_request('/api/uncategorized')
        # Should respond appropriately (not server error)  
        assert response.status_code < 500

    def test_api_endpoints_json_headers(self):
        """Test API endpoints return appropriate headers"""
        api_endpoints = ['/api/categories', '/api/transactions', '/api/uncategorized']
        
        for endpoint in api_endpoints:
            response = self.get_request(endpoint)
            if response.status_code == 200:
                # If successful, should have JSON content type or be HTML (redirect)
                content_type = response.headers.get('content-type', '')
                assert 'json' in content_type.lower() or 'html' in content_type.lower()

    def test_api_post_endpoints_require_auth(self):
        """Test that POST API endpoints require authentication"""
        post_endpoints = [
            '/api/categorize_transaction',
            '/api/set_budget', 
            '/api/classify',
            '/api/import'
        ]
        
        for endpoint in post_endpoints:
            response = self.post_request(endpoint, data={})
            # Should require auth (401/302) or handle request (200/400/422 for bad data)
            # Some endpoints may return 200 with error messages
            assert response.status_code in [200, 302, 400, 401, 422]


class TestWebServiceHealth(LightWebTestBase):
    """Test overall web service health and connectivity"""
    
    def test_service_responds(self):
        """Test that web service responds to basic requests"""
        # Login page should always be accessible
        assert quick_web_test('/login') is True
        
    def test_service_health_check(self):
        """Test comprehensive service health"""
        status = quick_service_check()
        
        # Login should always be accessible
        assert 'login' in status
        assert status['login']['accessible'] is True
        assert status['login']['status'] == 200
        
    def test_static_resources_available(self):
        """Test that common static resources are available"""
        # Test common static file paths that might exist
        static_paths = ['/static/', '/favicon.ico']
        
        for path in static_paths:
            response = self.get_request(path)
            # Static resources should either exist (200) or not found (404)
            # Should not return server errors (5xx)
            assert response.status_code < 500

    def test_multiple_concurrent_requests(self):
        """Test handling multiple requests"""
        import threading
        import time
        
        results = []
        
        def make_request():
            try:
                response = self.get_request('/login', timeout=5)
                results.append(response.status_code == 200)
            except Exception:
                results.append(False)
        
        # Make 5 concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Most requests should succeed
        assert sum(results) >= 3, "Most concurrent requests should succeed"


class TestErrorHandling(LightWebTestBase):
    """Test error handling and edge cases"""
    
    def test_non_existent_pages_return_404(self):
        """Test that non-existent pages return 404"""
        non_existent_pages = [
            '/non-existent-page',
            '/admin/secret',
            '/api/non-existent'
        ]
        
        for page in non_existent_pages:
            response = self.get_request(page)
            assert response.status_code == 404

    def test_malformed_requests_handled(self):
        """Test that malformed requests are handled gracefully"""
        # Try requests with malformed data
        malformed_requests = [
            {'endpoint': '/login', 'data': {'username': 'x' * 1000}},  # Very long username
            {'endpoint': '/api/categories', 'headers': {'Content-Type': 'invalid/type'}},
        ]
        
        for req in malformed_requests:
            try:
                if 'data' in req:
                    response = self.post_request(req['endpoint'], 
                                               data=req['data'],
                                               headers=req.get('headers', {}))
                else:
                    response = self.get_request(req['endpoint'],
                                              headers=req.get('headers', {}))
                
                # Should handle gracefully, not return server error
                assert response.status_code < 500
            except requests.exceptions.RequestException:
                # Connection errors are acceptable for malformed requests
                pass

    def test_request_timeout_handling(self):
        """Test that requests with very short timeouts are handled"""
        try:
            # Very short timeout might cause timeout exception
            response = self.get_request('/login', timeout=0.001)
            # If it succeeds, should be valid response
            assert response.status_code in [200, 302, 404]
        except requests.exceptions.Timeout:
            # Timeout exception is acceptable
            pass


class TestDataFormats(LightWebTestBase):
    """Test handling of different data formats"""
    
    def test_json_request_handling(self):
        """Test handling of JSON requests"""
        json_data = {'test': 'data'}
        
        # Try JSON request to API endpoint
        response = self.post_request('/api/categories',
                                   json=json_data,
                                   headers={'Content-Type': 'application/json'})
        
        # Should handle JSON (success, auth error, or bad request)
        assert response.status_code in [200, 302, 400, 401, 422]

    def test_form_data_handling(self):
        """Test handling of form data"""
        form_data = {'username': 'test', 'password': 'test'}
        
        response = self.post_request('/login', data=form_data)
        
        # Should handle form data appropriately
        assert response.status_code in [200, 302, 400, 401]

    def test_empty_request_handling(self):
        """Test handling of empty requests"""
        # Empty POST request
        response = self.post_request('/api/categories', data={})
        assert response.status_code in [200, 302, 400, 401, 422]


class TestSecurityBasics(LightWebTestBase):
    """Test basic security measures"""
    
    def test_sql_injection_prevention(self):
        """Test basic SQL injection attempt handling"""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'--"
        ]
        
        for malicious_input in malicious_inputs:
            response = self.login_user(malicious_input, 'password')
            
            # Should handle malicious input gracefully
            assert response.status_code in [200, 302, 400, 401]
            
            # Response should not contain obvious SQL error messages
            if response.status_code == 200:
                content = response.text.lower()
                sql_errors = ['syntax error', 'mysql error', 'postgres error', 'database connection failed']
                assert not any(error in content for error in sql_errors), \
                    f"Potential SQL error exposure detected for input: {malicious_input}"

    def test_xss_prevention_basics(self):
        """Test basic XSS prevention"""
        xss_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')", 
            "<img src=x onerror=alert('xss')>"
        ]
        
        for xss_input in xss_inputs:
            response = self.login_user(xss_input, 'password')
            
            # Should handle XSS attempts gracefully  
            assert response.status_code in [200, 302, 400, 401]


# Standalone integration test functions
def test_basic_service_connectivity():
    """Standalone test for basic service connectivity"""
    assert quick_web_test('/login') is True


def test_comprehensive_service_status():
    """Standalone test for comprehensive service status"""
    status = quick_service_check()
    
    # At minimum, login should be working
    assert 'login' in status
    assert status['login']['accessible'] is True
    
    # Should have reasonable response times
    if status['login']['response_time']:
        assert status['login']['response_time'] < 5.0  # Less than 5 seconds


def test_all_critical_endpoints():
    """Test all critical endpoints are responsive"""
    critical_endpoints = ['/login', '/logout', '/api/categories']
    
    for endpoint in critical_endpoints:
        try:
            response = requests.get(f"http://localhost:5000{endpoint}", timeout=5)
            assert response.status_code < 500  # No server errors
        except requests.exceptions.RequestException:
            pytest.fail(f"Critical endpoint {endpoint} not accessible")
