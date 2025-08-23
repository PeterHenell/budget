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
            'host': 'localhost',
            'port': 5432,
            'database': 'budget_db',
            'user': 'budget_user',
            'password': 'budget_password_2025'
        }
        
        print("🔍 Testing database connection...")
        db = BudgetDb(connection_params)
        if db.test_connection():
            print("✅ Database connection successful")
        else:
            pytest.fail("❌ Database connection failed")
            
        logic = BudgetLogic(connection_params)
        
        print("🔍 Testing add_transaction with confidence...")
        transaction_id = logic.add_transaction(
            date='2025-08-23',
            description='TEST CONFIDENCE ICA STORE',
            amount=-125.50,
            category_name='Mat',
            confidence=0.95,
            classification_method='hybrid-ai'
        )
        
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
