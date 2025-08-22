#!/usr/bin/env python3
"""
Quick test script for PostgreSQL database connection
"""
import os
import sys

# Add src directory to path
sys.path.append('/home/mrm/src/github/budget/src')

# Set environment variables for testing
os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_DB'] = 'budget_db'
os.environ['POSTGRES_USER'] = 'budget_user'
os.environ['POSTGRES_PASSWORD'] = 'budget_password_2025'
os.environ['POSTGRES_PORT'] = '5432'

try:
    from budget_db_postgres import BudgetDb
    print("✓ Successfully imported BudgetDb")
    
    db = BudgetDb()
    print("✓ Database connection established")
    
    categories = db.get_categories()
    print(f"✓ Found {len(categories)} categories: {categories}")
    
    db.close()
    print("✓ Database connection closed")
    print("\n🎉 PostgreSQL database test successful!")
    
except Exception as e:
    print(f"❌ Database test failed: {e}")
    sys.exit(1)
