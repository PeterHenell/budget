#!/usr/bin/env python3
"""
Database Initialization Script for Budget App
Handles table creation, indexes, default categories, and admin user setup
"""

import os
import sys
import psycopg2
import psycopg2.extras
from typing import Dict, Any, Optional


class DatabaseInitializer:
    """Handle database schema and data initialization"""
    
    def __init__(self, connection_params: Dict[str, Any] = None):
        """
        Initialize database initializer
        connection_params: dict with keys: host, database, user, password, port
        If None, reads from environment variables
        """
        if connection_params is None:
            connection_params = {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'database': os.getenv('POSTGRES_DB', 'budget_db'),
                'user': os.getenv('POSTGRES_USER', 'budget_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'budget_password'),
                'port': os.getenv('POSTGRES_PORT', '5432')
            }
        
        self.connection_params = connection_params
        self.conn = None
        
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            # Add connection timeout and other settings to prevent hanging
            self.connection_params['connect_timeout'] = 10
            self.connection_params['application_name'] = 'budget_db_init'
            
            self.conn = psycopg2.connect(**self.connection_params)
            self.conn.autocommit = True  # Use autocommit to prevent transaction issues
            
            # Set statement timeout to prevent hanging queries
            with self.conn.cursor() as cur:
                cur.execute("SET statement_timeout = '30s'")
                cur.execute("SET lock_timeout = '10s'")
                
            psycopg2.extras.register_default_json(globally=True)
            print(f"Connected to database: {self.connection_params['database']}")
        except psycopg2.Error as e:
            raise Exception(f"Failed to connect to PostgreSQL database: {e}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def needs_initialization(self) -> bool:
        """Check if database needs initialization"""
        try:
            with self.conn.cursor() as cur:
                # Check if essential tables exist
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('categories', 'transactions', 'budgets', 'users')
                """)
                table_count = cur.fetchone()[0]
                
                if table_count < 4:
                    return True
                
                # Check if we have default categories
                cur.execute("SELECT COUNT(*) FROM categories")
                category_count = cur.fetchone()[0]
                
                if category_count == 0:
                    return True
                
                # Check if admin user exists
                cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
                admin_count = cur.fetchone()[0]
                
                if admin_count == 0:
                    return True
                
                return False
        except Exception as e:
            # If we can't check, assume we need initialization
            print(f"Cannot check database status (assuming needs init): {e}")
            return True
            self.conn = None
    
    def create_tables(self):
        """Create all necessary database tables"""
        print("Creating database tables...")
        
        try:
            c = self.conn.cursor()
            
            # Create categories table
            print("  - Creating categories table...")
            c.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create budgets table
            print("  - Creating budgets table...")
            c.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id SERIAL PRIMARY KEY,
                    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
                    year INTEGER NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category_id, year)
                )
            """)
            
            # Create transactions table
            print("  - Creating transactions table...")
            c.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    verifikationsnummer VARCHAR(100),
                    date DATE NOT NULL,
                    description TEXT NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    classification_confidence DECIMAL(3,2) DEFAULT NULL,
                    classification_method VARCHAR(50) DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create users table for authentication
            print("  - Creating users table...")
            c.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role VARCHAR(50) DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Skip trigger creation to avoid hanging issues
            print("  - Skipping trigger creation (not required for basic functionality)")
            
            # Commit table creation - not needed with autocommit
            print("  ✓ All tables created successfully")
            
        except psycopg2.Error as e:
            raise Exception(f"Failed to create tables: {e}")
    
    def create_indexes(self):
        """Create database indexes for performance"""
        print("Creating database indexes...")
        
        try:
            c = self.conn.cursor()
            
            indexes = [
                ("idx_transactions_date", "transactions", "date"),
                ("idx_transactions_category", "transactions", "category_id"),
                ("idx_transactions_verification", "transactions", "verifikationsnummer"),
                ("idx_transactions_year_month", "transactions", "year, month"),
                ("idx_transactions_year", "transactions", "year"),
                ("idx_transactions_description", "transactions", "LOWER(description)"),
                ("idx_users_username", "users", "username"),
                ("idx_users_active", "users", "is_active"),
                ("idx_budgets_category_year", "budgets", "category_id, year"),
                ("idx_categories_name", "categories", "LOWER(name)")
            ]
            
            for idx_name, table, columns in indexes:
                print(f"  - Creating index: {idx_name}")
                c.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})")
            
            print("  ✓ All indexes created successfully")
            
        except psycopg2.Error as e:
            raise Exception(f"Failed to create indexes: {e}")
    
    def insert_default_categories(self):
        """Insert default budget categories"""
        print("Creating default categories...")
        
        default_categories = [
            "Mat",           # Food
            "Boende",        # Housing  
            "Transport",     # Transportation
            "Nöje",          # Entertainment
            "Hälsa",         # Health
            "Övrigt",        # Other
            "Uncategorized"  # Uncategorized
        ]
        
        try:
            c = self.conn.cursor()
            created_count = 0
            
            for cat in default_categories:
                try:
                    c.execute("INSERT INTO categories (name) VALUES (%s)", (cat,))
                    created_count += 1
                    print(f"  - Created category: {cat}")
                except psycopg2.IntegrityError:
                    # Category already exists, continue
                    print(f"  - Category already exists: {cat}")
                    continue
            
            print(f"  ✓ Created {created_count} new categories")
            
        except psycopg2.Error as e:
            raise Exception(f"Failed to create default categories: {e}")
    
    def create_admin_user(self, username: str = "admin", password: str = None):
        """Create admin user with secure password
        
        Args:
            username: Admin username (default: "admin")  
            password: Admin password (REQUIRED - no default for security)
        
        Raises:
            ValueError: If password is not provided
        """
        if password is None:
            raise ValueError("Password is required for security. No default password allowed.")
            
        print("Creating admin user...")
        
        try:
            import bcrypt
        except ImportError:
            print("  ⚠ bcrypt not available, skipping admin user creation")
            return
        
        try:
            c = self.conn.cursor()
            
            # Check if admin user exists
            c.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
            user_exists = c.fetchone()[0] > 0
            
            if not user_exists:
                # Create new admin user
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                c.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
                    (username, password_hash, "admin")
                )
                print(f"  ✓ Created admin user: {username} (password: {password})")
                print(f"  ⚠ Remember to change the default password!")
            else:
                # Update existing user to have admin role
                c.execute("UPDATE users SET role = %s WHERE username = %s", ("admin", username))
                print(f"  ✓ Updated existing user {username} to admin role")
                
        except psycopg2.Error as e:
            raise Exception(f"Failed to create admin user: {e}")
    
    def upgrade_existing_database(self):
        """Apply any necessary database upgrades to existing schemas"""
        print("Checking for database upgrades...")
        
        try:
            c = self.conn.cursor()
            
            # Add role column to users table if it doesn't exist
            try:
                c.execute("""
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user'
                """)
                print("  - Added role column to users table")
            except psycopg2.Error:
                pass
            
            # Add timestamps to tables if they don't exist
            timestamp_columns = [
                ("categories", "created_at"),
                ("budgets", "created_at"),
                ("budgets", "updated_at"),
                ("transactions", "created_at"),
                ("transactions", "updated_at"),
                ("users", "updated_at")
            ]
            
            for table, column in timestamp_columns:
                try:
                    c.execute(f"""
                        ALTER TABLE {table} 
                        ADD COLUMN IF NOT EXISTS {column} TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    """)
                    print(f"  - Added {column} to {table}")
                except psycopg2.Error:
                    pass
            
            print("  ✓ Database upgrades completed")
            
        except psycopg2.Error as e:
            print(f"  ⚠ Some database upgrades failed: {e}")
    
    def initialize_database(self, skip_admin: bool = False):
        """Run complete database initialization"""
        print("=" * 50)
        print("BUDGET APP - Database Initialization")
        print("=" * 50)
        
        try:
            self.connect()
            
            # Set a global timeout for all operations
            with self.conn.cursor() as cur:
                cur.execute("SET statement_timeout = '60s'")  # 60 second timeout for all statements
            
            self.create_tables()
            self.create_indexes()
            self.upgrade_existing_database()
            self.insert_default_categories()
            
            if not skip_admin:
                try:
                    # Generate a secure password for initial admin user
                    import secrets
                    import string
                    alphabet = string.ascii_letters + string.digits
                    admin_password = ''.join(secrets.choice(alphabet) for i in range(12))
                    self.create_admin_user(password=admin_password)
                    print(f"🔐 Admin user created with password: {admin_password}")
                    print("⚠️  IMPORTANT: Save this password securely and change it after first login!")
                except Exception as e:
                    print(f"⚠️  Admin user creation failed: {e}")
                    print("   Continuing without admin user...")
            
            print("=" * 50)
            print("✅ Database initialization completed successfully!")
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            raise
        finally:
            self.close()
        
    def auto_initialize_if_needed(self) -> bool:
        """
        Automatically initialize database if needed
        Returns True if initialization was performed, False if not needed
        """
        try:
            self.connect()
            
            if self.needs_initialization():
                print("🔧 Database needs initialization, starting auto-setup...")
                self.initialize_database(skip_admin=False)
                return True
            else:
                print("✅ Database already initialized, no action needed")
                return False
        except Exception as e:
            print(f"❌ Auto-initialization failed: {e}")
            raise
        finally:
            self.close()


def auto_initialize_database(connection_params: Dict[str, Any] = None) -> bool:
    """
    Convenience function for automatic database initialization
    Returns True if initialization was performed
    """
    initializer = DatabaseInitializer(connection_params)
    return initializer.auto_initialize_if_needed()


def main():
    """Main entry point for script execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Initialize Budget App Database')
    parser.add_argument('--skip-admin', action='store_true', 
                       help='Skip admin user creation')
    parser.add_argument('--host', default=os.getenv('POSTGRES_HOST', 'localhost'),
                       help='PostgreSQL host')
    parser.add_argument('--database', default=os.getenv('POSTGRES_DB', 'budget_db'),
                       help='Database name')
    parser.add_argument('--user', default=os.getenv('POSTGRES_USER', 'budget_user'),
                       help='Database user')
    parser.add_argument('--password', default=os.getenv('POSTGRES_PASSWORD', 'budget_password'),
                       help='Database password')
    parser.add_argument('--port', default=os.getenv('POSTGRES_PORT', '5432'),
                       help='Database port')
    
    args = parser.parse_args()
    
    connection_params = {
        'host': args.host,
        'database': args.database,
        'user': args.user,
        'password': args.password,
        'port': args.port
    }
    
    initializer = DatabaseInitializer(connection_params)
    initializer.initialize_database(skip_admin=args.skip_admin)


if __name__ == "__main__":
    main()
