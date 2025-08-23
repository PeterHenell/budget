#!/usr/bin/env python3
"""
Create test database for unit tests
"""
import psycopg2
import sys
import os

def create_test_database():
    """Create test database if it doesn't exist"""
    
    # Connect to PostgreSQL server (not to a specific database)
    admin_conn_params = {
        'host': os.getenv('POSTGRES_HOST', 'postgres'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'user': os.getenv('POSTGRES_USER', 'budget_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'budget_password_2025')
    }
    
    try:
        # Connect to postgres database to create the test database
        admin_conn_params['database'] = 'postgres'
        conn = psycopg2.connect(**admin_conn_params)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if test database exists
        test_db_name = 'budget_test_db'
        cursor.execute(
            "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s",
            (test_db_name,)
        )
        
        if not cursor.fetchone():
            print(f"Creating test database: {test_db_name}")
            cursor.execute(f'CREATE DATABASE "{test_db_name}"')
            print(f"✅ Test database '{test_db_name}' created successfully")
        else:
            print(f"✅ Test database '{test_db_name}' already exists")
        
        cursor.close()
        conn.close()
        
        # Now initialize the test database with tables
        print("Initializing test database schema...")
        import sys
        sys.path.insert(0, '/app')  # Add /app to path to find init_database.py
        from init_database import DatabaseInitializer
        
        test_conn_params = admin_conn_params.copy()
        test_conn_params['database'] = test_db_name
        
        db_init = DatabaseInitializer(test_conn_params)
        db_init.initialize_database(skip_admin=True)
        
        print("✅ Test database initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create test database: {e}")
        return False

if __name__ == "__main__":
    if create_test_database():
        sys.exit(0)
    else:
        sys.exit(1)
