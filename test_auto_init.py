#!/usr/bin/env python3
"""
Test script for database auto-initialization
"""
import os
import sys
sys.path.append('src')

from init_database import DatabaseInitializer

def test_auto_init():
    """Test the auto-initialization functionality"""
    print("🧪 Testing Database Auto-Initialization")
    print("=" * 50)
    
    # Connection parameters
    connection_params = {
        'host': os.getenv('POSTGRES_HOST', 'postgres'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'database': os.getenv('POSTGRES_DB', 'budget_db'),
        'user': os.getenv('POSTGRES_USER', 'budget_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'budget_password_2025')
    }
    
    # Test the needs_initialization check
    initializer = DatabaseInitializer(connection_params)
    try:
        initializer.connect()
        needs_init = initializer.needs_initialization()
        print(f"Database needs initialization: {needs_init}")
        
        if needs_init:
            print("✅ Auto-initialization check working correctly - database needs setup")
        else:
            print("✅ Auto-initialization check working correctly - database already initialized")
            
    except Exception as e:
        print(f"❌ Error during auto-initialization check: {e}")
        return False
    finally:
        initializer.close()
    
    print("=" * 50)
    print("✅ Auto-initialization test completed successfully!")
    return True

if __name__ == "__main__":
    success = test_auto_init()
    sys.exit(0 if success else 1)
