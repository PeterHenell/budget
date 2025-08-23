#!/usr/bin/env python3
"""
Simple initialization script for Budget App Database
Run this from the project root to initialize your database.
"""

import sys
import os

# Add src directory to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from init_database import DatabaseInitializer

def main():
    print("🏦 Budget App Database Initialization")
    print("=====================================")
    
    try:
        # Initialize with environment variables
        initializer = DatabaseInitializer()
        initializer.initialize_database()
        
        print("\n🎉 Success! Your database is ready to use.")
        print("\n📝 Next steps:")
        print("   1. Start the application: python src/web_app.py")
        print("   2. Login with admin/admin and change the password")
        print("   3. Start importing your transactions!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Make sure PostgreSQL is running")
        print("   2. Check your environment variables:")
        print("      - POSTGRES_HOST (default: localhost)")
        print("      - POSTGRES_DB (default: budget_db)")
        print("      - POSTGRES_USER (default: budget_user)")
        print("      - POSTGRES_PASSWORD (default: budget_password)")
        print("      - POSTGRES_PORT (default: 5432)")
        sys.exit(1)

if __name__ == "__main__":
    main()
