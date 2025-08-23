"""
Database layer for the Budget App
Handles all PostgreSQL database operations
"""

import psycopg2
import psycopg2.extras
import os
from typing import List, Dict, Optional, Tuple
from logging_config import get_logger


class BudgetDb:
    """Database abstraction layer for PostgreSQL operations"""
    
    def __init__(self, connection_params: dict = None, auto_init: bool = True):
        """
        Initialize database connection with optional parameters
        connection_params: dict with keys: host, database, user, password, port
        auto_init: whether to connect immediately and initialize tables
        """
        self.logger = get_logger(f'{__name__}.BudgetDb')
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
        self._connect_db()
        
        # Optional database initialization check
        if auto_init:
            self._check_and_init_db()

    def _connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            self.conn.autocommit = False  # Use transactions
            # Set up dict cursor for easier result handling
            psycopg2.extras.register_default_json(globally=True)
        except psycopg2.Error as e:
            raise Exception(f"Failed to connect to PostgreSQL database: {e}")

    def _check_and_init_db(self):
        """Check if database is initialized, warn if not"""
        try:
            c = self.conn.cursor()
            
            # Check if basic tables exist
            c.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'categories'
                );
            """)
            tables_exist = c.fetchone()[0]
            
            if not tables_exist:
                self.logger.warning("Database tables not found!")
                self.logger.info("Please run: python src/init_database.py")
                self.logger.info("Or use: from src.init_database import DatabaseInitializer")
                
        except psycopg2.Error as e:
            self.logger.warning(f"Could not check database initialization: {e}")

    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __del__(self):
        """Cleanup on destruction"""
        self.close()

    # === Category Operations ===
    
    def get_categories(self) -> List[str]:
        """Get all category names"""
        c = self.conn.cursor()
        c.execute("SELECT name FROM categories ORDER BY name")
        return [row[0] for row in c.fetchall()]

    def add_category(self, name: str):
        """Add a new category"""
        c = self.conn.cursor()
        try:
            c.execute("INSERT INTO categories (name) VALUES (%s)", (name,))
            self.conn.commit()
        except psycopg2.IntegrityError:
            self.conn.rollback()
            raise ValueError(f"Category '{name}' already exists")

    def remove_category(self, name: str):
        """Remove a category and cascade operations"""
        c = self.conn.cursor()
        try:
            # First get the category ID
            c.execute("SELECT id FROM categories WHERE name = %s", (name,))
            cat_row = c.fetchone()
            if not cat_row:
                raise ValueError(f"Category '{name}' not found")
            cat_id = cat_row[0]
            
            # Remove all associated budgets
            c.execute("DELETE FROM budgets WHERE category_id = %s", (cat_id,))
            
            # Remove category assignments from transactions (set to NULL)
            c.execute("UPDATE transactions SET category_id = NULL WHERE category_id = %s", (cat_id,))
            
            # Remove the category itself
            c.execute("DELETE FROM categories WHERE name = %s", (name,))
            
            if c.rowcount == 0:
                raise ValueError(f"Category '{name}' not found")
                
            self.conn.commit()
        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"Failed to remove category: {e}")

    def get_category_id(self, category_name: str) -> Optional[int]:
        """Get category ID by name"""
        c = self.conn.cursor()
        c.execute("SELECT id FROM categories WHERE name = %s", (category_name,))
        result = c.fetchone()
        return result[0] if result else None

    def get_category_name(self, category_id: int) -> Optional[str]:
        """Get category name by ID"""
        c = self.conn.cursor()
        c.execute("SELECT name FROM categories WHERE id = %s", (category_id,))
        result = c.fetchone()
        return result[0] if result else None

    # === Budget Operations ===
    
    def set_budget(self, category: str, year: int, amount: float):
        """Set yearly budget for a category"""
        c = self.conn.cursor()
        try:
            cat_id = self.get_category_id(category)
            if not cat_id:
                # Create the category if it doesn't exist
                self.add_category(category)
                cat_id = self.get_category_id(category)
                if not cat_id:
                    raise ValueError(f"Failed to create category: {category}")
            
            c.execute("""
                INSERT INTO budgets (category_id, year, amount)
                VALUES (%s, %s, %s)
                ON CONFLICT (category_id, year) 
                DO UPDATE SET amount = EXCLUDED.amount
            """, (cat_id, year, amount))
            self.conn.commit()
            return True
        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"Failed to set budget: {e}")

    def get_budget(self, category: str, year: int) -> float:
        """Get yearly budget for a category"""
        c = self.conn.cursor()
        cat_id = self.get_category_id(category)
        if not cat_id:
            raise ValueError("Category not found")
        
        c.execute("SELECT amount FROM budgets WHERE category_id = %s AND year = %s", (cat_id, year))
        result = c.fetchone()
        return float(result[0]) if result else 0.0

    def get_yearly_budgets(self, year: int) -> Dict[str, float]:
        """Get all budgets for a specific year"""
        c = self.conn.cursor()
        c.execute("""
            SELECT c.name, b.amount
            FROM categories c
            JOIN budgets b ON c.id = b.category_id
            WHERE b.year = %s
        """, (year,))
        return {row[0]: float(row[1]) for row in c.fetchall()}

    # === Transaction Operations ===
    
    def add_transaction(self, date: str, description: str, amount: float, 
                       category_name: str, verifikationsnummer: str = None,
                       confidence: float = None, method: str = None):
        """Add a new transaction with optional confidence tracking"""
        c = self.conn.cursor()
        try:
            # Get category ID, create if it doesn't exist
            cat_id = self.get_category_id(category_name)
            if not cat_id:
                self.add_category(category_name)
                cat_id = self.get_category_id(category_name)
            
            # Parse date for year/month
            year = int(date.split('-')[0])
            month = int(date.split('-')[1])
            
            c.execute("""
                INSERT INTO transactions (verifikationsnummer, date, description, amount, category_id, year, month,
                                        classification_confidence, classification_method)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (verifikationsnummer, date, description, amount, cat_id, year, month, confidence, method))
            self.conn.commit()
        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"Failed to add transaction: {e}")

    def get_transactions(self, category: str = None, year: int = None, 
                        limit: int = None, offset: int = None) -> List[Dict]:
        """Get transactions with optional filtering"""
        c = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = """
            SELECT t.id, t.verifikationsnummer, t.date, t.description, t.amount, 
                   c.name as category, t.year, t.month,
                   t.classification_confidence, t.classification_method,
                   t.created_at, t.updated_at
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
        """
        params = []
        
        conditions = []
        if category:
            conditions.append("c.name = %s")
            params.append(category)
        if year:
            conditions.append("t.year = %s")
            params.append(year)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY t.date DESC, t.id DESC"
        
        if limit:
            query += " LIMIT %s"
            params.append(limit)
            if offset:
                query += " OFFSET %s"
                params.append(offset)
        
        c.execute(query, params)
        return [dict(row) for row in c.fetchall()]

    def get_uncategorized_transactions(self, limit: int = None, offset: int = 0) -> List[Tuple]:
        """Get all uncategorized transactions with optional pagination"""
        c = self.conn.cursor()
        query = """
            SELECT t.id, t.verifikationsnummer, t.date, t.description, t.amount, t.year, t.month
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE c.name = 'Uncategorized' OR t.category_id IS NULL
            ORDER BY t.date DESC
        """
        params = []
        
        if limit:
            query += " LIMIT %s"
            params.append(limit)
            if offset:
                query += " OFFSET %s"
                params.append(offset)
        
        c.execute(query, params)
        return c.fetchall()

    def get_transaction_by_verification_number(self, verifikationsnummer: str) -> Optional[Dict]:
        """Get a single transaction by verification number for efficient lookup"""
        c = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("""
            SELECT t.id, t.verifikationsnummer, t.date, t.description, t.amount, 
                   t.year, t.month, t.category_id, c.name as category_name,
                   t.classification_confidence, t.classification_method,
                   t.created_at, t.updated_at
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.verifikationsnummer = %s
        """, (verifikationsnummer,))
        
        row = c.fetchone()
        if row:
            return dict(row)
        return None

    def classify_transaction(self, transaction_id: int, category_name: str, 
                           confidence: float = None, method: str = "Manual"):
        """Classify a transaction to a specific category with confidence tracking"""
        c = self.conn.cursor()
        try:
            cat_id = self.get_category_id(category_name)
            if not cat_id:
                # Create the category if it doesn't exist
                self.add_category(category_name)
                cat_id = self.get_category_id(category_name)
                if not cat_id:
                    raise ValueError(f"Failed to create category: {category_name}")
            
            # Update transaction with category and confidence info
            c.execute("""
                UPDATE transactions 
                SET category_id = %s, 
                    classification_confidence = %s,
                    classification_method = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (cat_id, confidence, method, transaction_id))
            
            if c.rowcount == 0:
                raise ValueError(f"Transaction with ID {transaction_id} not found")
            self.conn.commit()
            return True
        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"Failed to classify transaction: {e}")

    def import_transactions_bulk(self, transactions_data, category_name: str = "Uncategorized"):
        """Bulk import transactions"""
        c = self.conn.cursor()
        try:
            # Ensure Uncategorized category exists
            cat_id = self.get_category_id(category_name)
            if not cat_id:
                self.add_category(category_name)
                cat_id = self.get_category_id(category_name)
            
            for _, row in transactions_data.iterrows():
                c.execute("""
                    INSERT INTO transactions (verifikationsnummer, date, description, amount, category_id, year, month)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    row.get('Verifikationsnummer'),
                    row['Datum'],
                    row['Beskrivning'],
                    row['Belopp'],
                    cat_id,
                    row['year'],
                    row['month']
                ))
            
            self.conn.commit()
        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"Failed to import transactions: {e}")

    def delete_transaction(self, transaction_id: int):
        """Delete a single transaction by ID"""
        c = self.conn.cursor()
        try:
            c.execute("DELETE FROM transactions WHERE id = %s", (transaction_id,))
            if c.rowcount == 0:
                raise ValueError(f"Transaction with ID {transaction_id} not found")
            self.conn.commit()
            return True
        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"Failed to delete transaction: {e}")

    def delete_transactions_bulk(self, transaction_ids: List[int]):
        """Delete multiple transactions by their IDs"""
        if not transaction_ids:
            return 0
        
        c = self.conn.cursor()
        try:
            # Use IN clause for bulk deletion
            placeholders = ','.join(['%s'] * len(transaction_ids))
            c.execute(f"DELETE FROM transactions WHERE id IN ({placeholders})", transaction_ids)
            deleted_count = c.rowcount
            self.conn.commit()
            return deleted_count
        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"Failed to delete transactions: {e}")

    # === Reporting Operations ===
    
    def get_spending_report(self, year: int, month: int) -> List[Dict]:
        """Get spending vs yearly budget report for a specific month"""
        c = self.conn.cursor()
        c.execute("""
            SELECT cat.name, COALESCE(SUM(t.amount), 0) as spent, COALESCE(b.amount, 0) as budget
            FROM categories cat
            LEFT JOIN transactions t ON t.category_id = cat.id AND t.year = %s AND t.month = %s
            LEFT JOIN budgets b ON b.category_id = cat.id AND b.year = %s
            GROUP BY cat.name, b.amount
            ORDER BY cat.name
        """, (year, month, year))
        
        return [
            {
                'category': row[0],
                'spent': float(row[1]),
                'budget': float(row[2]),  # Yearly budget
                'diff': float(row[2]) - float(row[1])  # Budget minus spending for this month
            }
            for row in c.fetchall()
        ]

    def get_yearly_spending_report(self, year: int) -> List[Dict]:
        """Get spending vs yearly budget report for entire year"""
        c = self.conn.cursor()
        c.execute("""
            SELECT cat.name, COALESCE(SUM(t.amount), 0) as spent, COALESCE(b.amount, 0) as budget
            FROM categories cat
            LEFT JOIN transactions t ON t.category_id = cat.id AND t.year = %s
            LEFT JOIN budgets b ON b.category_id = cat.id AND b.year = %s
            GROUP BY cat.name, b.amount
            ORDER BY cat.name
        """, (year, year))
        
        return [
            {
                'category': row[0],
                'spent': float(row[1]),
                'budget': float(row[2]),
                'diff': float(row[2]) - float(row[1])
            }
            for row in c.fetchall()
        ]

    def get_all_budgets(self) -> List[Dict]:
        """Get all budget data"""
        c = self.conn.cursor()
        c.execute("""
            SELECT c.name as category, b.year, b.amount
            FROM budgets b
            JOIN categories c ON b.category_id = c.id
            ORDER BY b.year DESC, c.name
        """)
        
        return [
            {
                'category': row[0],
                'year': row[1],
                'amount': float(row[2])
            }
            for row in c.fetchall()
        ]

    # User management methods
    def authenticate_user(self, username: str, password: str) -> bool:
        """Authenticate a user with username and password"""
        try:
            import bcrypt
            c = self.conn.cursor()
            c.execute("SELECT password_hash FROM users WHERE username = %s AND is_active = TRUE", 
                     (username,))
            result = c.fetchone()
            
            if result:
                stored_hash = result[0]
                return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
            return False
        except ImportError:
            # bcrypt not available
            return False
        except psycopg2.Error as e:
            self.conn.rollback()
            return False

    def create_user(self, username: str, password: str, role: str = 'user') -> bool:
        """Create a new user with encrypted password"""
        try:
            import bcrypt
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            c = self.conn.cursor()
            c.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)", 
                     (username, password_hash, role))
            self.conn.commit()
            return True
        except (ImportError, psycopg2.Error):
            self.conn.rollback()
            return False

    def update_user_password(self, username: str, new_password: str) -> bool:
        """Update user password"""
        try:
            import bcrypt
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            c = self.conn.cursor()
            c.execute("UPDATE users SET password_hash = %s WHERE username = %s", 
                     (password_hash, username))
            self.conn.commit()
            return c.rowcount > 0
        except (ImportError, psycopg2.Error):
            self.conn.rollback()
            return False

    def list_users(self) -> List[Dict]:
        """List all active users"""
        try:
            c = self.conn.cursor()
            c.execute("""
                SELECT id, username, created_at, is_active, role 
                FROM users 
                ORDER BY username
            """)
            
            return [
                {
                    'id': row[0],
                    'username': row[1],
                    'created_at': row[2],
                    'active': row[3],
                    'role': row[4] if row[4] else 'user'
                }
                for row in c.fetchall()
            ]
        except psycopg2.Error:
            return []

    def get_user(self, username: str) -> Optional[Dict]:
        """Get user information"""
        try:
            c = self.conn.cursor()
            c.execute("SELECT username, role, created_at, is_active FROM users WHERE username = %s", (username,))
            row = c.fetchone()
            if row:
                return {
                    'username': row[0],
                    'role': row[1] if row[1] else 'user',
                    'created_at': row[2],
                    'is_active': row[3]
                }
            return None
        except psycopg2.Error:
            return None

    def is_admin(self, username: str) -> bool:
        """Check if user has admin role"""
        try:
            c = self.conn.cursor()
            c.execute("SELECT role FROM users WHERE username = %s", (username,))
            result = c.fetchone()
            return result and result[0] == 'admin'
        except psycopg2.Error:
            return False

    def update_user_role(self, username: str, new_role: str) -> bool:
        """Update user role"""
        try:
            c = self.conn.cursor()
            c.execute("UPDATE users SET role = %s WHERE username = %s", (new_role, username))
            self.conn.commit()
            return c.rowcount > 0
        except psycopg2.Error:
            self.conn.rollback()
            return False

    def toggle_user_status(self, username: str) -> bool:
        """Toggle user active status"""
        try:
            c = self.conn.cursor()
            c.execute("UPDATE users SET is_active = NOT is_active WHERE username = %s", (username,))
            self.conn.commit()
            return c.rowcount > 0
        except psycopg2.Error:
            self.conn.rollback()
            return False

    def delete_user(self, username: str) -> bool:
        """Delete a user"""
        try:
            c = self.conn.cursor()
            c.execute("DELETE FROM users WHERE username = %s", (username,))
            self.conn.commit()
            return c.rowcount > 0
        except psycopg2.Error:
            self.conn.rollback()
            return False
