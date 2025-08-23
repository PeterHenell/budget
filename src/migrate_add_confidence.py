#!/usr/bin/env python3
"""
Database Migration: Add Classification Confidence Tracking
Adds classification_confidence and classification_method columns to transactions table
"""

import os
import sys
import psycopg2
from typing import Dict, Any


class ConfidenceMigration:
    """Database migration to add confidence tracking"""
    
    def __init__(self, connection_params: Dict[str, Any] = None):
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
            self.conn.autocommit = False
            print(f"✅ Connected to database: {self.connection_params['database']}")
        except psycopg2.Error as e:
            raise Exception(f"❌ Failed to connect to database: {e}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def check_columns_exist(self) -> Dict[str, bool]:
        """Check if confidence columns already exist"""
        c = self.conn.cursor()
        
        # Check for classification_confidence column
        c.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'transactions' 
                AND column_name = 'classification_confidence'
            );
        """)
        confidence_exists = c.fetchone()[0]
        
        # Check for classification_method column  
        c.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'transactions' 
                AND column_name = 'classification_method'
            );
        """)
        method_exists = c.fetchone()[0]
        
        return {
            'classification_confidence': confidence_exists,
            'classification_method': method_exists
        }
    
    def add_confidence_columns(self):
        """Add confidence tracking columns to transactions table"""
        print("🔄 Adding confidence tracking columns...")
        
        try:
            c = self.conn.cursor()
            
            # Check which columns need to be added
            existing = self.check_columns_exist()
            
            if not existing['classification_confidence']:
                print("  📊 Adding classification_confidence column...")
                c.execute("""
                    ALTER TABLE transactions 
                    ADD COLUMN classification_confidence DECIMAL(3,2) DEFAULT NULL
                """)
            else:
                print("  ✅ classification_confidence column already exists")
            
            if not existing['classification_method']:
                print("  🔧 Adding classification_method column...")
                c.execute("""
                    ALTER TABLE transactions 
                    ADD COLUMN classification_method VARCHAR(50) DEFAULT NULL
                """)
            else:
                print("  ✅ classification_method column already exists")
            
            # Add helpful comment to the table
            c.execute("""
                COMMENT ON COLUMN transactions.classification_confidence IS 
                'Confidence score (0.00-1.00) for automatic classification'
            """)
            
            c.execute("""
                COMMENT ON COLUMN transactions.classification_method IS 
                'Method used for classification (e.g., RuleBase, LLM, SuperFast, Manual)'
            """)
            
            self.conn.commit()
            print("✅ Confidence tracking columns added successfully!")
            
        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"❌ Failed to add confidence columns: {e}")
    
    def update_existing_transactions(self):
        """Update existing manually classified transactions"""
        print("🔄 Updating existing transactions...")
        
        try:
            c = self.conn.cursor()
            
            # Count transactions that have categories but no confidence info
            c.execute("""
                SELECT COUNT(*) FROM transactions 
                WHERE category_id IS NOT NULL 
                AND classification_confidence IS NULL
            """)
            count = c.fetchone()[0]
            
            if count > 0:
                print(f"  📝 Updating {count} manually classified transactions...")
                
                # Set manual classification for existing categorized transactions
                c.execute("""
                    UPDATE transactions 
                    SET classification_confidence = 1.00,
                        classification_method = 'Manual'
                    WHERE category_id IS NOT NULL 
                    AND classification_confidence IS NULL
                """)
                
                self.conn.commit()
                print(f"  ✅ Updated {count} transactions with manual classification markers")
            else:
                print("  ✅ No existing transactions to update")
                
        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"❌ Failed to update existing transactions: {e}")
    
    def create_confidence_index(self):
        """Create index for confidence queries"""
        print("🔄 Creating performance indexes...")
        
        try:
            c = self.conn.cursor()
            
            # Index for filtering by confidence levels
            c.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_confidence 
                ON transactions(classification_confidence) 
                WHERE classification_confidence IS NOT NULL
            """)
            
            # Index for filtering by classification method
            c.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_method 
                ON transactions(classification_method) 
                WHERE classification_method IS NOT NULL
            """)
            
            self.conn.commit()
            print("  ✅ Performance indexes created")
            
        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"❌ Failed to create indexes: {e}")
    
    def run_migration(self):
        """Run the complete migration"""
        print("🚀 Starting Classification Confidence Migration")
        print("=" * 50)
        
        try:
            self.connect()
            
            # Check if transactions table exists
            c = self.conn.cursor()
            c.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'transactions'
                );
            """)
            
            if not c.fetchone()[0]:
                print("❌ Transactions table not found! Please initialize the database first.")
                return False
            
            # Run migration steps
            self.add_confidence_columns()
            self.update_existing_transactions()
            self.create_confidence_index()
            
            print("\n🎉 Migration completed successfully!")
            print("\nNew features available:")
            print("  • Confidence scores for all classifications")
            print("  • Visual confidence indicators in UI")
            print("  • Classification method tracking")
            print("  • Performance optimized queries")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            return False
        finally:
            self.close()


def main():
    """Run the migration"""
    print("Classification Confidence Migration Tool")
    print("Adds confidence tracking to the Budget App database")
    print()
    
    migration = ConfidenceMigration()
    success = migration.run_migration()
    
    if success:
        print("\n✅ Ready to use confidence-based classification!")
        sys.exit(0)
    else:
        print("\n❌ Migration failed - please check the errors above")
        sys.exit(1)


if __name__ == "__main__":
    main()
