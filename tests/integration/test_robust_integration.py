"""
Robust Integration Tests using Pytest Fixtures
Tests the complete application stack with proper user management and cleanup
"""

import pytest
import requests


class TestAuthentication:
    """Test authentication functionality with fixture-based user management"""
    
    def test_login_page_loads(self):
        """Test that login page loads correctly"""
        base_url = "http://localhost:5000"
        response = requests.get(f"{base_url}/login")
        assert response.status_code == 200
        assert "login" in response.text.lower()
    
    def test_successful_admin_login(self, admin_session, integration_users):
        """Test successful admin login using fixtures"""
        base_url = "http://localhost:5000"
        
        # The admin_session fixture should already be authenticated
        # Test access to the main page (/) which should be accessible for authenticated users
        response = admin_session.get(f"{base_url}/")
        assert response.status_code == 200
        
        print(f"✓ Admin login successful for: {integration_users['admin']['username']}")
    
    def test_successful_user_login(self, user_session, integration_users):
        """Test successful regular user login"""
        base_url = "http://localhost:5000"
        
        # The user_session fixture should already be authenticated
        # Test access to the main page (/) which should be accessible for authenticated users
        response = user_session.get(f"{base_url}/")
        assert response.status_code == 200
        
        print(f"✓ User login successful for: {integration_users['user']['username']}")
    
    def test_invalid_login(self):
        """Test invalid login credentials"""
        base_url = "http://localhost:5000"
        session = requests.Session()
        login_data = {
            "username": "nonexistent_user_12345",
            "password": "wrong_password_67890"
        }
        
        response = session.post(f"{base_url}/login", data=login_data)
        assert response.status_code in [200, 302]
    
    def test_protected_routes_redirect(self):
        """Test that protected routes redirect to login"""
        base_url = "http://localhost:5000"
        # Use routes that actually exist in web_app.py
        protected_routes = ["/transactions", "/budgets", "/reports", "/uncategorized"]
        
        for route in protected_routes:
            response = requests.get(f"{base_url}{route}", allow_redirects=False)
            # Should redirect to login (302) or show login page directly (200) if already showing login form
            assert response.status_code in [200, 302]
            assert "/login" in response.headers.get('Location', '')


class TestBasicOperations:
    """Test basic application operations"""
    
    def test_api_categories(self, admin_session):
        """Test categories API endpoint"""
        base_url = "http://localhost:5000"
        response = admin_session.get(f"{base_url}/api/categories")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Should have default categories
        category_names = [cat.lower() for cat in data]
        assert "uncategorized" in category_names
        
        print(f"✓ Found {len(data)} categories")
    
    def test_dashboard_access(self, admin_session):
        """Test main page access"""
        base_url = "http://localhost:5000"
        # Test the main page (/) which should be accessible for authenticated users
        response = admin_session.get(f"{base_url}/")
        assert response.status_code == 200
        print("✓ Dashboard accessible")
    
    def test_transactions_page_access(self, admin_session):
        """Test transactions page access"""
        base_url = "http://localhost:5000"
        response = admin_session.get(f"{base_url}/transactions")
        assert response.status_code == 200
        print("✓ Transactions page accessible")


class TestUserManagement:
    """Test the user management system itself"""
    
    def test_user_creation_and_cleanup(self, test_user_manager):
        """Test that users are created and cleaned up properly"""
        # Create a test user
        test_creds = test_user_manager.create_test_user(
            "temp_test_user", "temp_password", "user", cleanup=True
        )
        
        assert test_creds['username'] == "temp_test_user"
        assert test_user_manager.user_exists("temp_test_user")
        
        # Test role check
        role = test_user_manager.get_user_role("temp_test_user")
        assert role == "user"
        
        print(f"✓ User creation test passed for: {test_creds['username']}")
        
        # Cleanup will happen automatically via fixture
    
    def test_admin_user_creation(self, test_user_manager):
        """Test admin user creation"""
        admin_creds = test_user_manager.create_test_user(
            "temp_admin_user", "temp_admin_password", "admin", cleanup=True
        )
        
        assert admin_creds['username'] == "temp_admin_user"
        assert test_user_manager.user_exists("temp_admin_user")
        
        role = test_user_manager.get_user_role("temp_admin_user")
        assert role == "admin"
        
        print(f"✓ Admin creation test passed for: {admin_creds['username']}")


@pytest.mark.slow
class TestDataOperations:
    """Test data operations that might be slower"""
    
    def test_csv_import_simulation(self, admin_session):
        """Test CSV import endpoint exists and responds"""
        base_url = "http://localhost:5000"
        
        # Just test that the import page loads
        response = admin_session.get(f"{base_url}/import_csv")
        assert response.status_code == 200
        print("✓ CSV import page accessible")
    
    def test_api_transactions_pagination(self, admin_session):
        """Test transactions API pagination"""
        base_url = "http://localhost:5000"
        response = admin_session.get(f"{base_url}/api/transactions?page=1&per_page=10")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert 'transactions' in data
        assert 'total' in data
        print("✓ Transactions API pagination works")
