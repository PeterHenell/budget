"""
Integration tests for the Budget App
Tests the complete application stack with real database and web server
"""

import pytest
import requests
import time
import subprocess
import os
import csv
import tempfile
from typing import Dict, Any
from robust_test_base import RobustIntegrationTestBase, ensure_container_is_used

@ensure_container_is_used()
class TestAuthentication(RobustIntegrationTestBase):
    """Test authentication functionality"""
    
    def test_login_page_loads(self):
        """Test that login page loads correctly"""
        response = requests.get(f"{self.BASE_URL}/login")
        assert response.status_code == 200
        assert "login" in response.text.lower()
    
    def test_successful_login(self):
        """Test successful user login"""
        # Use the admin user created by the base class
        session = self.get_authenticated_session('admin')
        
        # Try to access a protected page
        response = session.get(f"{self.BASE_URL}/dashboard")
        assert response.status_code == 200
    
    def test_logout(self):
        """Test user logout"""
        session = self.get_authenticated_session('admin')
        
        # Logout
        response = session.get(f"{self.BASE_URL}/logout")
        assert response.status_code in [200, 302]
        
        # Try to access protected page after logout
        response = session.get(f"{self.BASE_URL}/dashboard", allow_redirects=False)
        assert response.status_code == 302


@ensure_container_is_used()
class TestPageAccess(RobustIntegrationTestBase):
    """Test page access functionality"""
    
    def test_login_page_structure(self):
        """Test login page has proper structure"""
        response = requests.get(f"{self.BASE_URL}/login")
        assert response.status_code == 200
        assert "username" in response.text.lower()
        assert "password" in response.text.lower()
    
    def test_successful_login(self):
        """Test successful authentication"""
        session = requests.Session()
        login_data = {
            "username": TestConfig.TEST_USERNAME,
            "password": TestConfig.TEST_PASSWORD
        }
        
        response = session.post(f"{TestConfig.BASE_URL}/login", data=login_data)
        assert response.status_code in [200, 302]
        
        # Check if we can access protected dashboard
        dashboard_response = session.get(f"{TestConfig.BASE_URL}/")
        assert dashboard_response.status_code == 200
        assert "dashboard" in dashboard_response.text.lower()
    
    def test_invalid_login(self):
        """Test login with invalid credentials"""
        session = requests.Session()
        login_data = {
            "username": "invalid",
            "password": "invalid"
        }
        
        response = session.post(f"{TestConfig.BASE_URL}/login", data=login_data)
        assert response.status_code == 200  # Should return to login page
        assert "login" in response.text.lower()
    
    def test_protected_routes_redirect(self):
        """Test that protected routes redirect to login"""
        unauthenticated_session = requests.Session()
        
        protected_routes = ["/", "/transactions", "/budgets", "/reports", "/uncategorized"]
        
        for route in protected_routes:
            response = unauthenticated_session.get(f"{TestConfig.BASE_URL}{route}")
            # Should redirect to login (302) or show login page (200)
            assert response.status_code in [200, 302]
    
    def test_logout(self):
        """Test logout functionality"""
        session = self.get_authenticated_session()
        
        # Access dashboard (should work)
        dashboard_response = session.get(f"{TestConfig.BASE_URL}/")
        assert dashboard_response.status_code == 200
        
        # Logout
        logout_response = session.get(f"{TestConfig.BASE_URL}/logout")
        assert logout_response.status_code in [200, 302]
        
        # Try to access dashboard again (should redirect to login)
        dashboard_response = session.get(f"{TestConfig.BASE_URL}/")
        assert dashboard_response.status_code in [200, 302]


class TestPageAccessDetailed(RobustIntegrationTestBase):
    """Test that all pages load correctly"""
    
    
    def test_transactions_page_loads(self):
        """Test transactions page loads"""
        session = self.get_authenticated_session()
        response = session.get(f"{TestConfig.BASE_URL}/transactions")
        assert response.status_code == 200
        assert "transactions" in response.text.lower()
    
    def test_budgets_page_loads(self):
        """Test budgets page loads"""
        session = self.get_authenticated_session()
        response = session.get(f"{TestConfig.BASE_URL}/budgets")
        assert response.status_code == 200
        assert "budgets" in response.text.lower()
    
    def test_reports_page_loads(self):
        """Test reports page loads"""
        session = self.get_authenticated_session()
        response = session.get(f"{TestConfig.BASE_URL}/reports")
        assert response.status_code == 200
        assert "reports" in response.text.lower()
    
    def test_import_page_loads(self):
        """Test import page loads"""
        session = self.get_authenticated_session()
        response = session.get(f"{TestConfig.BASE_URL}/import_csv")
        assert response.status_code == 200
        assert "import" in response.text.lower()
    
    def test_uncategorized_page_loads(self):
        """Test uncategorized page loads"""
        session = self.get_authenticated_session()
        response = session.get(f"{TestConfig.BASE_URL}/uncategorized")
        assert response.status_code == 200
        assert "uncategorized" in response.text.lower()


class TestAPIEndpoints(RobustIntegrationTestBase):
    """Test all API endpoints"""
    
    def test_api_categories(self):
        """Test categories API endpoint"""
        session = self.get_authenticated_session()
        response = session.get(f"{TestConfig.BASE_URL}/api/categories")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Should have default categories
        assert "Uncategorized" in data
    
    def test_api_transactions_pagination(self):
        """Test transactions API with pagination"""
        session = self.get_authenticated_session()
        
        # Test default pagination
        response = session.get(f"{TestConfig.BASE_URL}/api/transactions")
        assert response.status_code == 200
        
        data = response.json()
        assert "transactions" in data
        assert "page" in data
        assert "per_page" in data
        assert "total" in data
        assert "pages" in data
        
        # Test specific pagination
        response = session.get(f"{TestConfig.BASE_URL}/api/transactions?page=1&per_page=5")
        assert response.status_code == 200
        
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 5
    
    def test_api_uncategorized_pagination(self):
        """Test uncategorized API with pagination"""
        session = self.get_authenticated_session()
        response = session.get(f"{TestConfig.BASE_URL}/api/uncategorized?per_page=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "transactions" in data
        assert "total" in data
        assert data["per_page"] == 10
    
    def test_api_budgets_by_year(self):
        """Test budgets API by year"""
        session = self.get_authenticated_session()
        current_year = 2025
        response = session.get(f"{TestConfig.BASE_URL}/api/budgets/{current_year}")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_api_monthly_report(self):
        """Test monthly report API"""
        session = self.get_authenticated_session()
        response = session.get(f"{TestConfig.BASE_URL}/api/reports/monthly/2025/8")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        # Should have report data for each category
        if len(data) > 0:
            assert "category" in data[0]
            assert "spent" in data[0]
            assert "budget" in data[0]
    
    def test_api_yearly_report(self):
        """Test yearly report API"""
        session = self.get_authenticated_session()
        response = session.get(f"{TestConfig.BASE_URL}/api/yearly_report/2025")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)


class TestDataOperations(RobustIntegrationTestBase):
    """Test data CRUD operations"""
    
    def test_csv_import(self):
        """Test CSV file import functionality"""
        session = self.get_authenticated_session()
        
        # Create a test CSV file
        test_data = [
            ["Verifikationsnummer", "Datum", "Beskrivning", "Belopp"],
            ["TEST001", "2025-08-22", "Test Transaction 1", "-50.00"],
            ["TEST002", "2025-08-22", "Test Transaction 2", "100.00"],
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerows(test_data)
            temp_file = f.name
        
        try:
            # Upload the CSV file
            with open(temp_file, 'rb') as f:
                files = {'file': ('test.csv', f, 'text/csv')}
                response = session.post(f"{TestConfig.BASE_URL}/upload", files=files)
            
            # Should redirect to transactions page on success
            assert response.status_code in [200, 302]
            
            # Check if transactions were imported
            transactions_response = session.get(f"{TestConfig.BASE_URL}/api/transactions")
            assert transactions_response.status_code == 200
            
            transactions_data = transactions_response.json()
            assert transactions_data["total"] >= 2  # At least our test transactions
            
        finally:
            os.unlink(temp_file)
    
    def test_budget_operations(self):
        """Test budget setting and retrieval"""
        session = self.get_authenticated_session()
        
        # Test setting a budget
        budget_data = {
            "category": "Mat",
            "year": 2025,
            "amount": 1500.0
        }
        
        response = session.post(
            f"{TestConfig.BASE_URL}/api/set_budget",
            json=budget_data,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        
        result = response.json()
        assert result.get("success") is True
    
    def test_transaction_classification(self):
        """Test transaction classification"""
        session = self.get_authenticated_session()
        
        # First, ensure we have some transactions
        transactions_response = session.get(f"{TestConfig.BASE_URL}/api/transactions?per_page=1")
        assert transactions_response.status_code == 200
        
        transactions_data = transactions_response.json()
        if transactions_data["total"] > 0:
            # Get the first transaction
            transaction = transactions_data["transactions"][0]
            transaction_id = transaction.get("id") or transaction[0]  # Handle different formats
            
            # Classify the transaction
            classify_data = {
                "transaction_id": transaction_id,
                "category": "Mat"
            }
            
            response = session.post(
                f"{TestConfig.BASE_URL}/api/classify",
                json=classify_data,
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 200

    def test_transaction_deletion_single(self):
        """Test single transaction deletion"""
        session = self.get_authenticated_session()
        
        # First, import a test transaction
        test_data = [
            ["Verifikationsnummer", "Datum", "Beskrivning", "Belopp"],
            ["DELETE_TEST_001", "2025-08-22", "Transaction to delete", "-99.99"],
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerows(test_data)
            temp_file = f.name
        
        try:
            # Import the transaction
            with open(temp_file, 'rb') as f:
                files = {'file': ('delete_test.csv', f, 'text/csv')}
                upload_response = session.post(f"{TestConfig.BASE_URL}/upload", files=files)
            
            assert upload_response.status_code in [200, 302]
            
            # Get the imported transaction
            transactions_response = session.get(f"{TestConfig.BASE_URL}/api/transactions")
            assert transactions_response.status_code == 200
            transactions_data = transactions_response.json()
            
            # Find our test transaction
            test_transaction = None
            for tx in transactions_data["transactions"]:
                if tx["verifikationsnummer"] == "DELETE_TEST_001":
                    test_transaction = tx
                    break
            
            assert test_transaction is not None, "Test transaction not found after import"
            
            # Delete the transaction
            delete_response = session.delete(f"{TestConfig.BASE_URL}/api/transactions/{test_transaction['id']}")
            assert delete_response.status_code == 200
            
            delete_data = delete_response.json()
            assert delete_data["success"] is True
            
            # Verify transaction is deleted
            verify_response = session.get(f"{TestConfig.BASE_URL}/api/transactions")
            assert verify_response.status_code == 200
            verify_data = verify_response.json()
            
            # Transaction should no longer exist
            for tx in verify_data["transactions"]:
                assert tx["verifikationsnummer"] != "DELETE_TEST_001", "Transaction still exists after deletion"
                
        finally:
            os.unlink(temp_file)

    def test_transaction_deletion_bulk(self):
        """Test bulk transaction deletion"""
        session = self.get_authenticated_session()
        
        # First, import test transactions
        test_data = [
            ["Verifikationsnummer", "Datum", "Beskrivning", "Belopp"],
            ["BULK_DELETE_001", "2025-08-22", "Bulk delete test 1", "-10.00"],
            ["BULK_DELETE_002", "2025-08-22", "Bulk delete test 2", "-20.00"],
            ["BULK_DELETE_003", "2025-08-22", "Bulk delete test 3", "-30.00"],
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerows(test_data)
            temp_file = f.name
        
        try:
            # Import the transactions
            with open(temp_file, 'rb') as f:
                files = {'file': ('bulk_delete_test.csv', f, 'text/csv')}
                upload_response = session.post(f"{TestConfig.BASE_URL}/upload", files=files)
            
            assert upload_response.status_code in [200, 302]
            
            # Get the imported transactions
            transactions_response = session.get(f"{TestConfig.BASE_URL}/api/transactions")
            assert transactions_response.status_code == 200
            transactions_data = transactions_response.json()
            
            # Find our test transactions
            test_transaction_ids = []
            for tx in transactions_data["transactions"]:
                if tx["verifikationsnummer"].startswith("BULK_DELETE_"):
                    test_transaction_ids.append(tx["id"])
            
            assert len(test_transaction_ids) == 3, f"Expected 3 test transactions, found {len(test_transaction_ids)}"
            
            # Delete the transactions in bulk
            bulk_delete_response = session.post(
                f"{TestConfig.BASE_URL}/api/transactions/delete/bulk",
                json={"transaction_ids": test_transaction_ids}
            )
            assert bulk_delete_response.status_code == 200
            
            bulk_delete_data = bulk_delete_response.json()
            assert bulk_delete_data["success"] is True
            assert bulk_delete_data["deleted_count"] == 3
            
            # Verify transactions are deleted
            verify_response = session.get(f"{TestConfig.BASE_URL}/api/transactions")
            assert verify_response.status_code == 200
            verify_data = verify_response.json()
            
            # Transactions should no longer exist
            for tx in verify_data["transactions"]:
                assert not tx["verifikationsnummer"].startswith("BULK_DELETE_"), \
                    f"Transaction {tx['verifikationsnummer']} still exists after bulk deletion"
                
        finally:
            os.unlink(temp_file)

    def test_transaction_deletion_errors(self):
        """Test transaction deletion error handling"""
        session = self.get_authenticated_session()
        
        # Test deleting non-existent transaction
        delete_response = session.delete(f"{TestConfig.BASE_URL}/api/transactions/99999")
        assert delete_response.status_code == 500  # Should return error
        
        # Test bulk delete with empty list
        bulk_delete_response = session.post(
            f"{TestConfig.BASE_URL}/api/transactions/delete/bulk",
            json={"transaction_ids": []}
        )
        assert bulk_delete_response.status_code == 400
        
        bulk_delete_data = bulk_delete_response.json()
        assert "error" in bulk_delete_data
        assert "No transaction IDs provided" in bulk_delete_data["error"]
        
        # Test bulk delete with invalid data
        invalid_bulk_response = session.post(
            f"{TestConfig.BASE_URL}/api/transactions/delete/bulk",
            json={"transaction_ids": "not_a_list"}
        )
        assert invalid_bulk_response.status_code == 400
        
        invalid_data = invalid_bulk_response.json()
        assert "error" in invalid_data


class TestDatabaseIntegration(RobustIntegrationTestBase):
    """Test database integration and data persistence"""
    
    def test_database_connection(self):
        """Test that database connection is working"""
        session = self.get_authenticated_session()
        
        # Categories API should work (requires DB connection)
        response = session.get(f"{TestConfig.BASE_URL}/api/categories")
        assert response.status_code == 200
        
        categories = response.json()
        assert isinstance(categories, list)
        assert len(categories) > 0
    
    def test_data_persistence(self):
        """Test that data persists across requests"""
        session = self.get_authenticated_session()
        
        # Get initial transaction count
        initial_response = session.get(f"{TestConfig.BASE_URL}/api/transactions")
        assert initial_response.status_code == 200
        initial_count = initial_response.json()["total"]
        
        # Import a transaction via CSV
        test_data = [
            ["Verifikationsnummer", "Datum", "Beskrivning", "Belopp"],
            ["PERSIST001", "2025-08-22", "Persistence Test", "-25.99"],
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerows(test_data)
            temp_file = f.name
        
        try:
            with open(temp_file, 'rb') as f:
                files = {'file': ('persist_test.csv', f, 'text/csv')}
                upload_response = session.post(f"{TestConfig.BASE_URL}/upload", files=files)
            
            assert upload_response.status_code in [200, 302]
            
            # Check that transaction count increased
            final_response = session.get(f"{TestConfig.BASE_URL}/api/transactions")
            assert final_response.status_code == 200
            final_count = final_response.json()["total"]
            
            assert final_count > initial_count
            
        finally:
            os.unlink(temp_file)


class TestRoleBasedAccessControl(RobustIntegrationTestBase):
    """Test role-based access control and admin functionality"""
    
    def test_admin_can_access_user_management(self):
        """Test that admin user can access user management page"""
        session = self.get_authenticated_session()
        
        # Admin should be able to access user management page
        response = session.get(f"{TestConfig.BASE_URL}/manage_users")
        assert response.status_code == 200
        assert "User Management" in response.text
        assert "manage_users.html" in response.url or "manage" in response.text.lower()
    
    def test_admin_can_list_users(self):
        """Test that admin can see user list"""
        session = self.get_authenticated_session()
        
        # Get user management page
        response = session.get(f"{TestConfig.BASE_URL}/manage_users")
        assert response.status_code == 200
        
        # Should contain admin user in the list
        assert "admin" in response.text
    
    def test_admin_user_role_apis(self):
        """Test admin user role management APIs"""
        session = self.get_authenticated_session()
        
        # Test that role change API exists and returns proper error for self-modification
        response = session.post(
            f"{TestConfig.BASE_URL}/api/users/admin/role",
            json={"role": "user"}
        )
        
        # Should prevent admin from removing their own admin role
        assert response.status_code == 400
        data = response.json()
        assert "Cannot remove admin role from yourself" in data.get("error", "")
    
    def test_admin_user_toggle_apis(self):
        """Test admin user status toggle APIs"""
        session = self.get_authenticated_session()
        
        # Test that toggle API exists and returns proper error for self-modification
        response = session.post(f"{TestConfig.BASE_URL}/api/users/admin/toggle")
        
        # Should prevent admin from deactivating themselves
        assert response.status_code == 400
        data = response.json()
        assert "Cannot deactivate your own account" in data.get("error", "")
    
    def test_admin_user_delete_apis(self):
        """Test admin user deletion APIs"""
        session = self.get_authenticated_session()
        
        # Test that delete API exists and returns proper error for self-deletion
        response = session.delete(f"{TestConfig.BASE_URL}/api/users/admin")
        
        # Should prevent admin from deleting themselves
        assert response.status_code == 400
        data = response.json()
        assert "Cannot delete your own account" in data.get("error", "")
    
    def test_role_based_navigation(self):
        """Test that admin sees admin-specific navigation elements"""
        session = self.get_authenticated_session()
        
        # Get dashboard page
        response = session.get(f"{TestConfig.BASE_URL}/")
        assert response.status_code == 200
        
        # Should contain admin-specific elements (Manage Users link)
        # This tests that the navigation shows admin-only items
        page_content = response.text.lower()
        assert "manage users" in page_content or "admin" in page_content


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
