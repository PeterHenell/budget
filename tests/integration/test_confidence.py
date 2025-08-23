#!/usr/bin/env python3
"""
Test script for confidence tracking functionality
"""
import pytest
from logic import BudgetLogic
from budget_db_postgres import BudgetDb

class TestConfidenceTracking:
    """Test confidence tracking functionality"""
    
    def test_confidence_tracking_integration(self):
        """Test confidence tracking with database integration"""
        # Test database connection (use pytest fixtures for connection params)
        connection_params = {
            'host': 'postgres',
            'port': 5432,
            'database': 'budget_db',
            'user': 'budget_user',
            'password': 'budget_password_2025'
        }
        
        print("🔍 Testing database connection...")
        db = BudgetDb(connection_params)
        try:
            # Simple connection test - try to get categories
            categories = db.get_categories()
            print(f"✅ Database connection successful - found {len(categories)} categories")
        except Exception as e:
            pytest.fail(f"❌ Database connection failed: {e}")
            
        logic = BudgetLogic(connection_params)
        
        print("🔍 Testing add_transaction with confidence...")
        try:
            transaction_id = logic.add_transaction(
                date='2025-08-23',
                description='TEST CONFIDENCE ICA STORE',
                amount=-125.50,
                category_name='Mat',
                confidence=0.95,
                classification_method='hybrid-ai'
            )
            print(f"Debug: add_transaction returned: {transaction_id}")
        except Exception as e:
            print(f"Error in add_transaction: {e}")
            transaction_id = None
        
        if transaction_id:
            print(f"✅ Transaction added with ID: {transaction_id}")
            
            # Test reclassification with confidence
            print("🔍 Testing reclassification with confidence...")
            success = logic.reclassify_transaction(
                transaction_id, 
                'Nöje', 
                confidence=0.75, 
                classification_method='manual'
            )
            
            if success:
                print("✅ Reclassification with confidence successful")
                
                # Verify the confidence was stored correctly
                transactions = logic.db.get_transactions(limit=1)
                if transactions and transactions[0]['id'] == transaction_id:
                    tx = transactions[0]
                    assert tx.get('classification_confidence') == 0.75
                    assert tx.get('classification_method') == 'manual'
                    assert tx.get('category') == 'Nöje'
                    print(f"✅ Confidence verification: {tx.get('classification_confidence')}")
                else:
                    pytest.fail("❌ Could not retrieve updated transaction")
            else:
                pytest.fail("❌ Reclassification failed")
        else:
            pytest.fail("❌ Failed to add transaction")
            
        logic.close()
        print("✅ Confidence tracking test completed successfully!")

if __name__ == '__main__':
    test = TestConfidenceTracking()
    test.test_confidence_tracking_integration()
