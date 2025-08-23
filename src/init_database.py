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
            self.conn = psycopg2.connect(**self.connection_params)
            self.conn.autocommit = False  # Use transactions
            psycopg2.extras.register_default_json(globally=True)
            print(f"Connected to database: {self.connection_params['database']}")
        except psycopg2.Error as e:
            raise Exception(f"Failed to connect to PostgreSQL database: {e}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
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
            
            # Create updated_at trigger function
            print("  - Creating updated_at trigger function...")
            c.execute("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """)
            
            # Create triggers for updated_at columns
            print("  - Creating updated_at triggers...")
            trigger_tables = ['budgets', 'transactions', 'users']
            for table in trigger_tables:
                c.execute(f"""
                    DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
                    CREATE TRIGGER update_{table}_updated_at 
                        BEFORE UPDATE ON {table} 
                        FOR EACH ROW 
                        EXECUTE FUNCTION update_updated_at_column();
                """)
            
            # Commit table creation
            self.conn.commit()
            print("  ✓ All tables created successfully")
            
        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"Failed to create tables: {e}")
    
    def create_indexes(self):
        """Create database indexes for performance"""
        print("Creating database indexes...")
        
        try:
            c = self.conn.cursor()
            
            indexes = [
                ("idx_transactions_date", "transactions", "date"),
                ("idx_transactions_category", "transactions", "category_id"),
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
            
            self.conn.commit()
            print("  ✓ All indexes created successfully")
            
        except psycopg2.Error as e:
            self.conn.rollback()
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
                    self.conn.commit()
                    created_count += 1
                    print(f"  - Created category: {cat}")
                except psycopg2.IntegrityError:
                    # Category already exists, rollback and continue
                    self.conn.rollback()
                    print(f"  - Category already exists: {cat}")
                    continue
            
            print(f"  ✓ Created {created_count} new categories")
            
        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"Failed to create default categories: {e}")
    
    def create_admin_user(self, username: str = "admin", password: str = "admin"):
        """Create default admin user"""
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
                self.conn.commit()
                print(f"  ✓ Created admin user: {username} (password: {password})")
                print(f"  ⚠ Remember to change the default password!")
            else:
                # Update existing user to have admin role
                c.execute("UPDATE users SET role = %s WHERE username = %s", ("admin", username))
                self.conn.commit()
                print(f"  ✓ Updated existing user {username} to admin role")
                
        except psycopg2.Error as e:
            self.conn.rollback()
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
            
            self.conn.commit()
            print("  ✓ Database upgrades completed")
            
        except psycopg2.Error as e:
            self.conn.rollback()
            print(f"  ⚠ Some database upgrades failed: {e}")
    
    def initialize_database(self, skip_admin: bool = False):
        """Run complete database initialization"""
        print("=" * 50)
        print("BUDGET APP - Database Initialization")
        print("=" * 50)
        
        try:
            self.connect()
            self.create_tables()
            self.create_indexes()
            self.upgrade_existing_database()
            self.insert_default_categories()
            
            if not skip_admin:
                self.create_admin_user()
            
            print("=" * 50)
            print("✅ Database initialization completed successfully!")
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            raise
        finally:
            self.close()


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
