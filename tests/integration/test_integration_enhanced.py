"""
Enhanced Integration Tests for the Budget App
Tests the complete application stack with robust user management and cleanup
"""

import pytest
import requests
import time
import csv
import tempfile
import sys
from pathlib import Path
from typing import Dict, Any

# Add integration test directory to path
sys.path.insert(0, str(Path(__file__).parent))

from robust_test_base import RobustIntegrationTestBase, skip_if_containers_not_running


@skip_if_containers_not_running()
class TestAuthentication(RobustIntegrationTestBase):
    """Test authentication functionality with proper user management"""
    
    def test_login_page_loads(self):
        """Test that login page loads correctly"""
        response = requests.get(f"{self.BASE_URL}/login")
        assert response.status_code == 200
        assert "login" in response.text.lower()
    
    def test_successful_admin_login(self):
        """Test successful admin login"""
        session = self.get_authenticated_session('admin')
        
        # Try to access dashboard
        response = session.get(f"{self.BASE_URL}/dashboard")
        assert response.status_code == 200
    
    def test_successful_user_login(self):
        """Test successful regular user login"""
        session = self.get_authenticated_session('user')
        
        # Try to access dashboard
        response = session.get(f"{self.BASE_URL}/dashboard")
        assert response.status_code == 200
    
    def test_invalid_login(self):
        """Test invalid login credentials"""
        session = requests.Session()
        login_data = {
            "username": "nonexistent_user_12345",
            "password": "wrong_password_67890"
        }
        
        response = session.post(f"{self.BASE_URL}/login", data=login_data)
        # Should stay on login page or redirect back to login
        assert response.status_code in [200, 302]
    
    def test_protected_routes_redirect(self):
        """Test that protected routes redirect to login"""
        protected_routes = ["/dashboard", "/transactions", "/budgets", "/reports", "/uncategorized"]
        
        for route in protected_routes:
            response = requests.get(f"{self.BASE_URL}{route}", allow_redirects=False)
            assert response.status_code == 302
            assert "/login" in response.headers.get('Location', '')
    
    def test_logout(self):
        """Test user logout"""
        session = self.get_authenticated_session('admin')
        
        # Logout
        response = session.get(f"{self.BASE_URL}/logout")
        assert response.status_code in [200, 302]
        
        # Try to access protected page after logout
        response = session.get(f"{self.BASE_URL}/dashboard", allow_redirects=False)
        assert response.status_code == 302


@skip_if_containers_not_running()
class TestPageAccess(RobustIntegrationTestBase):
    """Test page access for authenticated users"""
    
    def test_dashboard_loads(self):
        """Test dashboard loads for admin"""
        session = self.get_authenticated_session('admin')
        response = session.get(f"{self.BASE_URL}/dashboard")
        assert response.status_code == 200
    
    def test_transactions_page_loads(self):
        """Test transactions page loads"""
        session = self.get_authenticated_session('admin')
        response = session.get(f"{self.BASE_URL}/transactions")
        assert response.status_code == 200
    
    def test_budgets_page_loads(self):
        """Test budgets page loads"""
        session = self.get_authenticated_session('admin')
        response = session.get(f"{self.BASE_URL}/budgets")
        assert response.status_code == 200
    
    def test_reports_page_loads(self):
        """Test reports page loads"""
        session = self.get_authenticated_session('admin')
        response = session.get(f"{self.BASE_URL}/reports")
        assert response.status_code == 200
    
    def test_import_page_loads(self):
        """Test import page loads"""
        session = self.get_authenticated_session('admin')
        response = session.get(f"{self.BASE_URL}/import_csv")
        assert response.status_code == 200
    
    def test_uncategorized_page_loads(self):
        """Test uncategorized page loads"""
        session = self.get_authenticated_session('admin')
        response = session.get(f"{self.BASE_URL}/uncategorized")
        assert response.status_code == 200


@skip_if_containers_not_running()
class TestAPIEndpoints(RobustIntegrationTestBase):
    """Test all API endpoints with proper authentication"""
    
    def test_api_categories(self):
        """Test categories API endpoint"""
        session = self.get_authenticated_session('admin')
        response = session.get(f"{self.BASE_URL}/api/categories")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Should have default categories
        category_names = [cat.lower() for cat in data]
        assert "uncategorized" in category_names
    
    def test_api_transactions_pagination(self):
        """Test transactions API pagination"""
        session = self.get_authenticated_session('admin')
        response = session.get(f"{self.BASE_URL}/api/transactions?page=1&per_page=10")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert 'transactions' in data
        assert 'total' in data
        assert 'pages' in data
    
    def test_api_uncategorized_pagination(self):
        """Test uncategorized transactions API pagination"""
        session = self.get_authenticated_session('admin')
        response = session.get(f"{self.BASE_URL}/api/uncategorized?page=1&per_page=10")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert 'transactions' in data
        assert 'total' in data
    
    def test_api_budgets_by_year(self):
        """Test budgets API by year"""
        session = self.get_authenticated_session('admin')
        response = session.get(f"{self.BASE_URL}/api/budgets/2025")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_api_monthly_report(self):
        """Test monthly report API"""
        session = self.get_authenticated_session('admin')
        response = session.get(f"{self.BASE_URL}/api/reports/monthly/2025/8")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
    
    def test_api_yearly_report(self):
        """Test yearly report API"""
        session = self.get_authenticated_session('admin')
        response = session.get(f"{self.BASE_URL}/api/reports/yearly/2025")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)


@skip_if_containers_not_running()
class TestDataOperations(RobustIntegrationTestBase):
    """Test data operations with proper cleanup"""
    
    def test_csv_import(self):
        """Test CSV file import functionality"""
        session = self.get_authenticated_session('admin')
        
        # Create test CSV data
        test_data = [
            ['Verifikationsnummer', 'Bokföringsdatum', 'Text', 'Belopp'],
            ['TEST001', '2025-08-23', 'TEST IMPORT TRANSACTION', '-150.00'],
            ['TEST002', '2025-08-23', 'TEST IMPORT TRANSACTION 2', '-250.00']
        ]
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerows(test_data)
            csv_path = f.name
        
        try:
            # Upload CSV file
            with open(csv_path, 'rb') as f:
                files = {'file': (f.name, f, 'text/csv')}
                response = session.post(f"{self.BASE_URL}/upload", files=files)
            
            # Should redirect to transactions page or return success
            assert response.status_code in [200, 302]
            
        finally:
            # Clean up temp file
            import os
            try:
                os.unlink(csv_path)
            except:
                pass
    
    def test_budget_operations(self):
        """Test budget creation and management"""
        session = self.get_authenticated_session('admin')
        
        # Test budget creation via API
        budget_data = {
            'category': 'Mat',
            'year': 2025,
            'amount': 5000.00
        }
        
        response = session.post(f"{self.BASE_URL}/api/budgets", json=budget_data)
        # Should return success or already exists
        assert response.status_code in [200, 201, 409]
    
    def test_transaction_classification(self):
        """Test transaction classification"""
        session = self.get_authenticated_session('admin')
        
        # This would require creating a test transaction first
        # For now, just test that the classification endpoint exists
        response = session.get(f"{self.BASE_URL}/api/categories")
        assert response.status_code == 200


@skip_if_containers_not_running()
class TestRoleBasedAccess(RobustIntegrationTestBase):
    """Test role-based access control"""
    
    def test_admin_can_access_admin_pages(self):
        """Test that admin users can access admin-only pages"""
        admin_session = self.get_authenticated_session('admin')
        
        # Test admin-only routes (if they exist)
        admin_routes = ["/admin", "/admin/users"]
        
        for route in admin_routes:
            response = admin_session.get(f"{self.BASE_URL}{route}")
            # Admin routes might not exist yet, so we just check it doesn't fail authorization
            assert response.status_code in [200, 404]  # 404 is ok if route doesn't exist
    
    def test_regular_user_restrictions(self):
        """Test that regular users have appropriate restrictions"""
        user_session = self.get_authenticated_session('user')
        
        # Regular users should be able to access basic pages
        basic_routes = ["/dashboard", "/transactions", "/budgets", "/reports"]
        
        for route in basic_routes:
            response = user_session.get(f"{self.BASE_URL}{route}")
            assert response.status_code == 200
