#!/usr/bin/env python3
"""
Test script for PostgreSQL database connection
"""
import pytest
from budget_db_postgres import BudgetDb

class TestDatabaseConnection:
    """Test database connectivity"""
    
    def test_database_connection(self):
        """Test that we can connect to the database"""
        db = BudgetDb()
        assert db is not None
        
        # Test that connection is working by getting categories
        categories = db.get_categories()
        assert isinstance(categories, list)
        
        db.close()
    
    def test_get_categories(self):
        """Test that we can retrieve categories from the database"""
        db = BudgetDb()
        
        categories = db.get_categories()
        assert isinstance(categories, list)
        assert len(categories) >= 0  # Should have at least 0 categories
        
        db.close()
    
    def test_database_operations(self):
        """Test basic database operations"""
        db = BudgetDb()
        
        # Test getting categories (should not fail)
        categories = db.get_categories()
        print(f"✓ Found {len(categories)} categories")
        
        # Test connection is still working by getting categories again
        categories2 = db.get_categories()
        assert isinstance(categories2, list)
        assert len(categories2) == len(categories)
        
        db.close()
        print("✓ Database operations test completed")

if __name__ == '__main__':
    # Allow running as standalone script for debugging
    test = TestDatabaseConnection()
    try:
        test.test_database_connection()
        test.test_get_categories()
        test.test_database_operations()
        print("🎉 All database tests passed!")
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        raise
