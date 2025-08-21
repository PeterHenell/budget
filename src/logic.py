import pandas as pd
import sqlite3
import os
import tempfile
import base64
import hashlib
import atexit
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class BudgetLogic:
    def __init__(self, db_path, password):
        self.db_path = db_path
        self.password = password
        self.conn = None
        self.fernet = self._get_fernet(password)
        self.temp_db_path = None
        self._changes_pending = False
        self.default_categories = [
            "Mat", "Boende", "Transport", "Nöje", "Hälsa", "Övrigt", "Uncategorized"
        ]
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
        c = self.conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )
        """)
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
        for cat in self.default_categories:
            try:
                c.execute("INSERT INTO categories (name) VALUES (?)", (cat,))
            except sqlite3.IntegrityError:
                pass
        self.conn.commit()

    def get_categories(self):
        c = self.conn.cursor()
        c.execute("SELECT name FROM categories")
        return [row[0] for row in c.fetchall()]

    def add_category(self, name):
        c = self.conn.cursor()
        try:
            c.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            self.conn.commit()
            self._mark_changes()
        except sqlite3.IntegrityError:
            raise ValueError(f"Category '{name}' already exists")

    def remove_category(self, name):
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

    def set_budget(self, category, year, amount):
        """Set yearly budget for a category"""
        c = self.conn.cursor()
        c.execute("SELECT id FROM categories WHERE name=?", (category,))
        cat_id = c.fetchone()
        if not cat_id:
            raise ValueError("Category not found")
        cat_id = cat_id[0]
        c.execute("""
            INSERT INTO budgets (category_id, year, amount)
            VALUES (?, ?, ?)
            ON CONFLICT(category_id, year) DO UPDATE SET amount=excluded.amount
        """, (cat_id, year, amount))
        self.conn.commit()
        self._mark_changes()

    def get_budget(self, category, year, month=None):
        """Get yearly budget for a category (month parameter kept for compatibility but ignored)"""
        c = self.conn.cursor()
        c.execute("SELECT id FROM categories WHERE name=?", (category,))
        cat_id = c.fetchone()
        if not cat_id:
            return 0.0
        cat_id = cat_id[0]
        c.execute("SELECT amount FROM budgets WHERE category_id=? AND year=?", (cat_id, year))
        row = c.fetchone()
        return row[0] if row else 0.0

    def import_csv(self, csv_path):
        try:
            # Try semicolon first (Swedish format), then comma
            try:
                df = pd.read_csv(csv_path, sep=';')
            except Exception:
                df = pd.read_csv(csv_path, sep=',')
                
            # Swedish headers: 'Verifikationsnummer', 'Bokföringsdatum', 'Text', 'Belopp'
            column_mapping = {
                'Verifikationsnummer': 'verifikationsnummer',
                'Bokföringsdatum': 'date',
                'Text': 'description', 
                'Belopp': 'amount'
            }
            
            # Map available columns
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df = df.rename(columns={old_col: new_col})
                    
            # Drop extra date column if it exists
            if 'Valutadatum' in df.columns:
                df = df.drop('Valutadatum', axis=1)
                    
            # Validate required columns
            required_cols = ['verifikationsnummer', 'date', 'description', 'amount']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
                
            # Clean and convert data
            df['amount'] = pd.to_numeric(df['amount'].astype(str).str.replace(',', '.'), errors='coerce')
            df = df.dropna(subset=['amount'])
            
            df['year'] = pd.to_datetime(df['date']).dt.year
            df['month'] = pd.to_datetime(df['date']).dt.month
            
            # Import transactions
            c = self.conn.cursor()
            
            # Get or create the "Uncategorized" category
            c.execute("SELECT id FROM categories WHERE name='Uncategorized'")
            uncategorized_row = c.fetchone()
            if not uncategorized_row:
                # Create Uncategorized category if it doesn't exist
                c.execute("INSERT INTO categories (name) VALUES ('Uncategorized')")
                self.conn.commit()
                c.execute("SELECT id FROM categories WHERE name='Uncategorized'")
                uncategorized_row = c.fetchone()
            uncategorized_id = uncategorized_row[0]
            
            imported_count = 0
            for _, row in df.iterrows():
                c.execute("""
                    INSERT INTO transactions (verifikationsnummer, date, description, amount, year, month, category_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (row['verifikationsnummer'], row['date'], row['description'], 
                      row['amount'], row['year'], row['month'], uncategorized_id))
                imported_count += 1
            
            self.conn.commit()
            self._mark_changes()
            return imported_count
            
        except Exception as e:
            raise ValueError(f"Failed to import CSV: {e}")

    def get_unclassified_transactions(self):
        c = self.conn.cursor()
        c.execute("SELECT verifikationsnummer, date, description, amount FROM transactions WHERE category_id IS NULL")
        return c.fetchall()

    def get_uncategorized_transactions(self, limit=None, offset=0):
        """Get transactions in the 'Uncategorized' category (queue of transactions to be processed)"""
        c = self.conn.cursor()
        # Get Uncategorized category ID
        c.execute("SELECT id FROM categories WHERE name='Uncategorized'")
        uncategorized_row = c.fetchone()
        if not uncategorized_row:
            return []
        
        uncategorized_id = uncategorized_row[0]
        
        # Build query with optional limit and offset for pagination
        query = """
            SELECT id, verifikationsnummer, date, description, amount, year, month 
            FROM transactions 
            WHERE category_id = ? 
            ORDER BY date DESC, id DESC
        """
        params = [uncategorized_id]
        
        if limit:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        c.execute(query, params)
        return c.fetchall()

    def get_uncategorized_count(self):
        """Get total count of uncategorized transactions"""
        c = self.conn.cursor()
        c.execute("SELECT id FROM categories WHERE name='Uncategorized'")
        uncategorized_row = c.fetchone()
        if not uncategorized_row:
            return 0
        
        uncategorized_id = uncategorized_row[0]
        c.execute("SELECT COUNT(*) FROM transactions WHERE category_id = ?", (uncategorized_id,))
        return c.fetchone()[0]

    def reclassify_transaction(self, transaction_id, category_name):
        """Move a transaction from Uncategorized to a specific category"""
        c = self.conn.cursor()
        
        # Get category ID
        c.execute("SELECT id FROM categories WHERE name=?", (category_name,))
        cat_row = c.fetchone()
        if not cat_row:
            raise ValueError("Category not found")
        cat_id = cat_row[0]
        
        # Update transaction
        c.execute("UPDATE transactions SET category_id=? WHERE id=?", (cat_id, transaction_id))
        if c.rowcount == 0:
            raise ValueError("Transaction not found")
        
        self.conn.commit()
        self._mark_changes()

    def classify_transaction(self, verifikationsnummer, category):
        c = self.conn.cursor()
        c.execute("SELECT id FROM categories WHERE name=?", (category,))
        cat_id = c.fetchone()
        if not cat_id:
            raise ValueError("Category not found")
        cat_id = cat_id[0]
        c.execute("UPDATE transactions SET category_id=? WHERE verifikationsnummer=?", (cat_id, verifikationsnummer))
        if c.rowcount == 0:
            raise ValueError("Transaction not found")
        self.conn.commit()
        self._mark_changes()

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
                'budget': row[2],  # Yearly budget
                'diff': row[2] - row[1]  # Budget minus spending for entire year
            }
            for row in c.fetchall()
        ]
    def close(self):
        """Explicitly close and encrypt the database"""
        self._cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ...existing code...
