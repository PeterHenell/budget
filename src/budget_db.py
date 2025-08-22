"""
Database layer for the Budget App
Handles all SQLite database operations with encryption support
"""

import sqlite3
import os
import tempfile
import base64
import atexit
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class BudgetDb:
    """Database abstraction layer for encrypted SQLite operations"""
    
    def __init__(self, db_path, password):
        self.db_path = db_path
        self.password = password
        self.conn = None
        self.fernet = self._get_fernet(password)
        self.temp_db_path = None
        self._changes_pending = False
        
        try:
            self._decrypt_db()
            self._connect_db()
            self._init_db()
            # Register cleanup on exit
            atexit.register(self._cleanup)
        except Exception:
            self._cleanup()
            raise

    def _get_fernet(self, password):
        """Generate encryption key from password"""
        # Use proper key derivation with salt
        salt = b'budget_app_salt_2025'  # In production, use random salt stored with file
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)

    def _decrypt_db(self):
        """Decrypt database file to temporary location"""
        if not os.path.exists(self.db_path):
            # No DB yet, create temp file
            fd, self.temp_db_path = tempfile.mkstemp(suffix='.db')
            os.close(fd)  # Close file descriptor but keep the path
            return
        
        with open(self.db_path, "rb") as f:
            encrypted = f.read()
        try:
            decrypted = self.fernet.decrypt(encrypted)
        except Exception as e:
            raise ValueError(f"Incorrect password or corrupted database file: {e}")
        
        fd, self.temp_db_path = tempfile.mkstemp(suffix='.db')
        with os.fdopen(fd, "wb") as f:
            f.write(decrypted)

    def _connect_db(self):
        """Connect to the decrypted database"""
        self.conn = sqlite3.connect(self.temp_db_path)
        
    def _mark_changes(self):
        """Mark that changes have been made and need encryption on close"""
        self._changes_pending = True
        
    def _encrypt_db(self):
        """Encrypt the database file"""
        if not self.conn or not self.temp_db_path:
            return
            
        # Close connection before reading
        self.conn.close()
        
        try:
            with open(self.temp_db_path, "rb") as f:
                plain = f.read()
            encrypted = self.fernet.encrypt(plain)
            
            # Write to temp file first, then move to avoid corruption
            temp_encrypted = self.db_path + '.tmp'
            with open(temp_encrypted, "wb") as f:
                f.write(encrypted)
            os.replace(temp_encrypted, self.db_path)
            
        finally:
            # Reconnect for continued use
            self.conn = sqlite3.connect(self.temp_db_path)
            
        self._changes_pending = False
        
    def _cleanup(self):
        """Clean up resources and encrypt if needed"""
        try:
            if self._changes_pending:
                self._encrypt_db()
            if self.conn:
                self.conn.close()
                self.conn = None
        except Exception:
            pass  # Ignore cleanup errors
        finally:
            if self.temp_db_path and os.path.exists(self.temp_db_path):
                try:
                    os.remove(self.temp_db_path)
                except Exception:
                    pass

    def _init_db(self):
        """Initialize database schema"""
        c = self.conn.cursor()
        
        # Create categories table
        c.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )
        """)
        
        # Create budgets table
        c.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY,
            category_id INTEGER,
            year INTEGER,
            amount REAL,
            UNIQUE(category_id, year),
            FOREIGN KEY(category_id) REFERENCES categories(id)
        )
        """)
        
        # Create transactions table
        c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            verifikationsnummer TEXT,
            date TEXT,
            description TEXT,
            amount REAL,
            category_id INTEGER,
            year INTEGER,
            month INTEGER,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        )
        """)
        self.conn.commit()
        
        # Insert default categories if not present
        default_categories = [
            "Mat", "Boende", "Transport", "Nöje", "Hälsa", "Övrigt", "Uncategorized"
        ]
        for cat in default_categories:
            try:
                c.execute("INSERT INTO categories (name) VALUES (?)", (cat,))
            except sqlite3.IntegrityError:
                pass
        self.conn.commit()

    def close(self):
        """Explicitly close the database connection"""
        self._cleanup()

    # === Category Operations ===
    
    def get_categories(self):
        """Get all category names"""
        c = self.conn.cursor()
        c.execute("SELECT name FROM categories")
        return [row[0] for row in c.fetchall()]

    def add_category(self, name):
        """Add a new category"""
        c = self.conn.cursor()
        try:
            c.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            self.conn.commit()
            self._mark_changes()
        except sqlite3.IntegrityError:
            raise ValueError(f"Category '{name}' already exists")

    def remove_category(self, name):
        """Remove a category and cascade operations"""
        c = self.conn.cursor()
        
        # First get the category ID
        c.execute("SELECT id FROM categories WHERE name=?", (name,))
        cat_row = c.fetchone()
        if not cat_row:
            raise ValueError(f"Category '{name}' not found")
        cat_id = cat_row[0]
        
        # Remove all associated budgets
        c.execute("DELETE FROM budgets WHERE category_id=?", (cat_id,))
        
        # Remove category assignments from transactions (set to NULL)
        c.execute("UPDATE transactions SET category_id=NULL WHERE category_id=?", (cat_id,))
        
        # Remove the category itself
        c.execute("DELETE FROM categories WHERE name=?", (name,))
        
        if c.rowcount == 0:
            raise ValueError(f"Category '{name}' not found")
        self.conn.commit()
        self._mark_changes()

    def get_category_id(self, category_name):
        """Get category ID by name"""
        c = self.conn.cursor()
        c.execute("SELECT id FROM categories WHERE name=?", (category_name,))
        result = c.fetchone()
        return result[0] if result else None

    def get_category_name(self, category_id):
        """Get category name by ID"""
        c = self.conn.cursor()
        c.execute("SELECT name FROM categories WHERE id=?", (category_id,))
        result = c.fetchone()
        return result[0] if result else None

    # === Budget Operations ===
    
    def set_budget(self, category, year, amount):
        """Set yearly budget for a category"""
        c = self.conn.cursor()
        cat_id = self.get_category_id(category)
        if not cat_id:
            raise ValueError("Category not found")
        
        c.execute("""
            INSERT INTO budgets (category_id, year, amount)
            VALUES (?, ?, ?)
            ON CONFLICT(category_id, year) DO UPDATE SET amount=excluded.amount
        """, (cat_id, year, amount))
        self.conn.commit()
        self._mark_changes()

    def get_budget(self, category, year):
        """Get yearly budget for a category"""
        c = self.conn.cursor()
        cat_id = self.get_category_id(category)
        if not cat_id:
            raise ValueError("Category not found")
        
        c.execute("SELECT amount FROM budgets WHERE category_id=? AND year=?", (cat_id, year))
        result = c.fetchone()
        return result[0] if result else 0

    def get_yearly_budgets(self, year):
        """Get all budgets for a specific year"""
        c = self.conn.cursor()
        c.execute("""
            SELECT c.name, b.amount
            FROM categories c
            JOIN budgets b ON c.id = b.category_id
            WHERE b.year = ?
        """, (year,))
        return {row[0]: row[1] for row in c.fetchall()}

    # === Transaction Operations ===
    
    def add_transaction(self, date, description, amount, category_name, verifikationsnummer=None):
        """Add a new transaction"""
        c = self.conn.cursor()
        
        # Get category ID, create if it doesn't exist
        cat_id = self.get_category_id(category_name)
        if not cat_id:
            self.add_category(category_name)
            cat_id = self.get_category_id(category_name)
        
        # Parse date for year/month
        year = int(date.split('-')[0])
        month = int(date.split('-')[1])
        
        c.execute("""
            INSERT INTO transactions (verifikationsnummer, date, description, amount, category_id, year, month)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (verifikationsnummer, date, description, amount, cat_id, year, month))
        self.conn.commit()
        self._mark_changes()

    def get_transactions(self, category=None, year=None, limit=None, offset=None):
        """Get transactions with optional filtering"""
        c = self.conn.cursor()
        
        query = """
            SELECT t.id, t.verifikationsnummer, t.date, t.description, t.amount, 
                   c.name as category, t.year, t.month
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
        """
        params = []
        
        conditions = []
        if category:
            conditions.append("c.name = ?")
            params.append(category)
        if year:
            conditions.append("t.year = ?")
            params.append(year)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY t.date DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
            if offset:
                query += " OFFSET ?"
                params.append(offset)
        
        c.execute(query, params)
        
        columns = ['id', 'verifikationsnummer', 'date', 'description', 'amount', 'category', 'year', 'month']
        return [dict(zip(columns, row)) for row in c.fetchall()]

    def get_uncategorized_transactions(self, limit=None, offset=0):
        """Get all uncategorized transactions with optional pagination"""
        c = self.conn.cursor()
        query = """
            SELECT t.id, t.verifikationsnummer, t.date, t.description, t.amount, t.year, t.month
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE c.name = 'Uncategorized' OR (t.category_id IS NULL)
            ORDER BY t.date DESC
        """
        params = []
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
            if offset:
                query += " OFFSET ?"
                params.append(offset)
        
        c.execute(query, params)
        return c.fetchall()

    def classify_transaction(self, transaction_id, category_name):
        """Classify a transaction to a specific category"""
        c = self.conn.cursor()
        cat_id = self.get_category_id(category_name)
        if not cat_id:
            raise ValueError(f"Category '{category_name}' not found")
        
        c.execute("UPDATE transactions SET category_id=? WHERE id=?", (cat_id, transaction_id))
        self.conn.commit()
        self._mark_changes()

    def import_transactions_bulk(self, transactions_data, category_name="Uncategorized"):
        """Bulk import transactions"""
        c = self.conn.cursor()
        
        # Ensure Uncategorized category exists
        cat_id = self.get_category_id(category_name)
        if not cat_id:
            self.add_category(category_name)
            cat_id = self.get_category_id(category_name)
        
        for _, row in transactions_data.iterrows():
            c.execute("""
                INSERT INTO transactions (verifikationsnummer, date, description, amount, category_id, year, month)
                VALUES (?, ?, ?, ?, ?, ?, ?)
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
        self._mark_changes()

    # === Reporting Operations ===
    
    def get_spending_report(self, year, month):
        """Get spending vs yearly budget report for a specific month"""
        c = self.conn.cursor()
        c.execute("""
            SELECT cat.name, IFNULL(SUM(t.amount), 0), IFNULL(b.amount, 0)
            FROM categories cat
            LEFT JOIN transactions t ON t.category_id = cat.id AND t.year=? AND t.month=?
            LEFT JOIN budgets b ON b.category_id = cat.id AND b.year=?
            GROUP BY cat.name
        """, (year, month, year))
        return [
            {
                'category': row[0],
                'spent': row[1],
                'budget': row[2],  # Yearly budget
                'diff': row[2] - row[1]  # Budget minus spending for this month
            }
            for row in c.fetchall()
        ]

    def get_yearly_spending_report(self, year):
        """Get spending vs yearly budget report for entire year"""
        c = self.conn.cursor()
        c.execute("""
            SELECT cat.name, IFNULL(SUM(t.amount), 0), IFNULL(b.amount, 0)
            FROM categories cat
            LEFT JOIN transactions t ON t.category_id = cat.id AND t.year=?
            LEFT JOIN budgets b ON b.category_id = cat.id AND b.year=?
            GROUP BY cat.name
        """, (year, year))
        return [
            {
                'category': row[0],
                'spent': row[1],
                'budget': row[2],
                'diff': row[2] - row[1]
            }
            for row in c.fetchall()
        ]

    def get_all_budgets(self):
        """Get all budget data"""
        c = self.conn.cursor()
        c.execute("""
            SELECT c.name as category, b.year, b.amount
            FROM budgets b
            JOIN categories c ON b.category_id = c.id
            ORDER BY b.year DESC, c.name
        """)
        
        columns = ['category', 'year', 'amount']
        return [dict(zip(columns, row)) for row in c.fetchall()]
