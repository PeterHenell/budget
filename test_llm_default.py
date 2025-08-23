#!/usr/bin/env python3
"""
Test script to verify LLM-supported classification is working as default
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, '/app/src')

from logic import BudgetLogic
from auto_classify import AutoClassificationEngine
import pandas as pd
import tempfile

def test_llm_default_classification():
    """Test that LLM classifiers are prioritized and working by default"""
    
    print("🧪 Testing LLM-supported classification as default...")
    
    # Initialize logic with PostgreSQL connection
    connection_params = {
        'host': 'postgres',
        'port': 5432,
        'database': 'budget_test_db',
        'user': 'budget_user',
        'password': 'budget_password_2025'
    }
    
    logic = BudgetLogic(connection_params)
    
    # Test 1: Check AutoClassificationEngine initialization
    print("\n1️⃣ Testing AutoClassificationEngine initialization...")
    engine = AutoClassificationEngine(logic)
    
    print(f"   ✅ Engine has {len(engine.classifiers)} classifiers")
    for i, classifier in enumerate(engine.classifiers):
        classifier_name = classifier.__class__.__name__
        print(f"   {i+1}. {classifier_name}")
        
    # Test 2: Test classification with sample transaction
    print("\n2️⃣ Testing transaction classification...")
    
    sample_transaction = {
        'description': 'ICA SUPERMARKET STOCKHOLM',
        'amount': -250.50,
        'date': '2025-08-23',
        'year': 2025,
        'month': 8
    }
    
    suggestions = engine.classify_transaction(sample_transaction)
    
    if suggestions:
        print(f"   ✅ Got {len(suggestions)} classification suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"      {i}. {suggestion['category']} "
                  f"({suggestion['confidence']:.1%} confidence, "
                  f"{suggestion['classifier']}, "
                  f"type: {suggestion.get('type', 'unknown')})")
                  
        # Check if LLM classifier is prioritized
        if suggestions[0].get('type') == 'llm':
            print("   🎯 LLM classifier is prioritized - SUCCESS!")
        else:
            print("   ⚠️  Traditional classifier came first")
    else:
        print("   ❌ No classification suggestions returned")
    
    # Test 3: Test import with auto-classification
    print("\n3️⃣ Testing CSV import with automatic LLM classification...")
    
    # Create test CSV
    test_data = {
        'Verifikationsnummer': ['TEST001', 'TEST002'],
        'Bokföringsdatum': ['2025-08-23', '2025-08-23'],
        'Text': ['ICA SUPERMARKET STOCKHOLM', 'SHELL BENSINSTATION'],
        'Belopp': [-150.00, -500.00]
    }
    
    df = pd.DataFrame(test_data)
    test_csv = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
    df.to_csv(test_csv.name, index=False, sep=';')
    test_csv.close()
    
    try:
        # Import should trigger automatic classification
        imported_count = logic.import_csv(test_csv.name)
        print(f"   ✅ Imported {imported_count} transactions")
        print("   📈 Automatic LLM classification should have triggered during import")
        
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
    finally:
        os.unlink(test_csv.name)
    
    print("\n🏁 Test completed!")

if __name__ == "__main__":
    test_llm_default_classification()
