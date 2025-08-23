#!/usr/bin/env python3
"""
Test script for confidence tracking functionality
"""
import sys
import os
sys.path.append('/home/mrm/src/github/budget/src')

# Test database connection and confidence functionality
def test_confidence_tracking():
    try:
        from logic import BudgetLogic
        from budget_db_postgres import BudgetDb
        
        print("✅ Imports successful")
        
        # Test database connection (without Docker environment variables)
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
            print("❌ Database connection failed")
            return
            
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
            else:
                print("❌ Reclassification failed")
        else:
            print("❌ Failed to add transaction")
            
        logic.close()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    test_confidence_tracking()
