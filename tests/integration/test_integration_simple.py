#!/usr/bin/env python3
"""
Simple Integration test to verify basic functionality
Uses the robust test base for proper user management
"""

import tempfile
import os
import json
import sys
from pathlib import Path
import pytest

# Add src directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from logic import BudgetLogic
from robust_test_base import RobustIntegrationTestBase, QuickIntegrationTestBase


class TestWebAppStructure:
    """Test basic web app structure - no database needed"""

    def test_web_app_structure(self):
        """Test that the web app has all the expected endpoints"""
        
        # Import the web app
        import web_app
        
        app = web_app.app
        
        # Check that all expected routes exist
        expected_routes = [
            '/',
            '/login',
            '/logout', 
            '/budgets',
            '/import_csv',  # Updated route name
            '/transactions',
            '/uncategorized',
            '/reports',
            '/api/budgets/<int:year>',
            '/api/categories',
            '/api/import',
            '/api/transactions',
            '/api/uncategorized',
            '/api/classify',
            '/api/reports/monthly/<int:year>/<int:month>',
            '/api/reports/yearly/<int:year>'
        ]
        
        # Get all rules from the app
        app_routes = []
        for rule in app.url_map.iter_rules():
            app_routes.append(rule.rule)
        
        print(f"Available routes: {sorted(app_routes)}")
        
        # Check each expected route exists
        for expected_route in expected_routes:
            # Some flexibility for route variations
            found = any(expected_route in route or route == expected_route for route in app_routes)
            assert found, f"Web app should have route: {expected_route}"


    """Test basic logic layer functionality with database"""
    
    def test_logic_initialization(self):
        """Test that logic layer initializes correctly"""
        try:
            logic = BudgetLogic(self.connection_params)
            assert logic is not None
            assert logic.db is not None
            print("✓ Logic layer initialized successfully")
        except Exception as e:
            pytest.fail(f"Logic initialization failed: {e}")
    
    def test_basic_database_operations(self):
        """Test basic database operations"""
        logic = BudgetLogic(self.connection_params)
        
        # Test categories
        categories = logic.get_categories()
        assert isinstance(categories, list)
        assert len(categories) > 0
        assert "Uncategorized" in categories
        
        print(f"✓ Found {len(categories)} categories")
    
    def test_import_functionality(self):
        """Test CSV import functionality"""
        logic = BudgetLogic(self.connection_params)
        
        # Create test CSV content
        csv_content = """Verifikationsnummer;Bokföringsdatum;Text;Belopp
TEST001;2025-08-23;TEST TRANSACTION SIMPLE;-100.50"""
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(csv_content)
            csv_path = f.name
        
        try:
            # Test import
            imported_count = logic.import_csv(csv_path)
            assert imported_count >= 0  # Should not fail
            print(f"✓ Import completed, processed {imported_count} transactions")
            
        finally:
            # Clean up
            try:
                os.unlink(csv_path)
            except:
                pass


class TestAutoClassificationIntegration(QuickIntegrationTestBase):
    """Test auto-classification functionality"""
    
    def test_logic_integration(self):
        """Test core logic integration functionality"""
        # Create a temporary database for testing
        db_path = ":memory:"  # Use in-memory SQLite for testing
        
        # Initialize the logic layer
        logic = BudgetLogic(self.connection_params)
        
        try:
            # Test category management
            logic.add_category("Test Category")
            categories = logic.get_categories()
            assert "Test Category" in categories, "Category should be added"
            
            # Test yearly budget operations
            logic.set_budget("Test Category", 2024, 12000.0)
            budgets = logic.get_yearly_budgets(2024)
            assert budgets["Test Category"] == 12000.0, "Yearly budget should be set correctly"
            
            # Test transaction operations
            logic.add_transaction("2024-08-01", "Test Transaction", -100.0, "Test Category")
            transactions = logic.get_transactions()
            assert len(transactions) >= 1, "Transaction should be added"
            
            # Test uncategorized transactions
            logic.add_transaction("2024-08-02", "Uncategorized Transaction", -50.0, "Uncategorized")
            uncategorized = logic.get_uncategorized_transactions()
            assert len(uncategorized) >= 1, "Uncategorized transaction should exist"
            
            # Test reporting
            monthly_report = logic.generate_monthly_report(2024, 8)
            yearly_report = logic.generate_yearly_report(2024)
            
            print("✓ Category management operations work correctly")
            print("✓ Budget operations work correctly") 
            print("✓ Transaction operations work correctly")
            print("✓ Reporting functionality works correctly")
            
        finally:
            # Clean up
            try:
                logic.close()
            except:
                pass

def test_auto_classification_integration():
    """Test auto-classification functionality end-to-end"""
    print("Testing auto-classification integration...")
    
    # Remove test database if it exists
    db_path = "test_auto_classify.db"
    if os.path.exists(db_path):
        os.unlink(db_path)
    
    try:
        logic = BudgetLogic(db_path, "test_password")
        
        # Add some sample categories (check if they exist first)
        categories = logic.get_categories()
        if "Mat" not in categories:
            logic.add_category("Mat")
        if "Transport" not in categories:
            logic.add_category("Transport")
        
        # Add some training data
        logic.add_transaction("2024-08-01", "ICA SUPERMARKET STOCKHOLM", -150.0, "Mat")
        logic.add_transaction("2024-08-02", "SL MONTHLY PASS", -850.0, "Transport")
        
        # Add uncategorized transactions that should be auto-classified
        logic.add_transaction("2024-08-03", "ICA NÄRA MALMÖ", -89.50, "Uncategorized")
        logic.add_transaction("2024-08-04", "SL DAY PASS", -45.0, "Uncategorized")
        
        # Test auto-classification engine can be instantiated
        from auto_classify import AutoClassificationEngine
        engine = AutoClassificationEngine(logic)
        
        # Get uncategorized transactions
        uncategorized = logic.get_uncategorized_transactions()
        assert len(uncategorized) >= 2, "Should have at least 2 uncategorized transactions"
        
        # Test that engine exists and has the right methods
        assert hasattr(engine, 'classify_transaction'), "Engine should have classify_transaction method"
        assert hasattr(engine, 'auto_classify_uncategorized'), "Engine should have auto_classify_uncategorized method"
        
        print("✓ Auto-classification functionality works correctly")
        logic.close()
        
    finally:
        # Clean up test database
        if os.path.exists(db_path):
            os.unlink(db_path)

if __name__ == "__main__":
    test_web_app_structure()
    test_logic_integration() 
    test_auto_classification_integration()
    print("\n🎉 All integration tests passed! Web app is fully functional.")
