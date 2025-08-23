import os
import pandas as pd
from budget_db_postgres import BudgetDb
from logging_config import get_logger

class BudgetLogic:
    """Business logic layer for the Budget App"""
    
    def __init__(self, connection_params=None):
        """Initialize with database connection parameters or use environment variables"""
        self.db = BudgetDb(connection_params)
        self.logger = get_logger(f'{__name__}.BudgetLogic')
        
    def close(self):
        """Close the database connection"""
        self.db.close()

    @property
    def conn(self):
        """Compatibility property for tests - provides access to database connection"""
        return self.db.conn

    # === Category Management ===
    
    def get_categories(self):
        """Get all category names"""
        return self.db.get_categories()

    def add_category(self, name):
        """Add a new category"""
        return self.db.add_category(name)

    def remove_category(self, name):
        """Remove a category and all associated data"""
        return self.db.remove_category(name)

    # === Budget Management ===
    
    def set_budget(self, category, year, amount):
        """Set yearly budget for a category"""
        return self.db.set_budget(category, year, amount)

    def get_budget(self, category, year):
        """Get yearly budget for a category"""
        return self.db.get_budget(category, year)

    def get_yearly_budgets(self, year):
        """Get all budgets for a specific year"""
        return self.db.get_yearly_budgets(year)
    
    def set_yearly_budget(self, category, year, amount):
        """Set yearly budget (alias for compatibility)"""
        return self.set_budget(category, year, amount)

    def get_all_budgets(self):
        """Get all budget data"""
        return self.db.get_all_budgets()

    # === Transaction Management ===
    
    def add_transaction(self, date, description, amount, category_name, verifikationsnummer=None, confidence=None, classification_method=None):
        """Add a new transaction"""
        return self.db.add_transaction(date, description, amount, category_name, verifikationsnummer, confidence, classification_method)

    def get_transactions(self, category=None, year=None, limit=None, offset=None):
        """Get transactions with optional filtering"""
        return self.db.get_transactions(category, year, limit, offset)

    def get_uncategorized_transactions(self, limit=None, offset=0):
        """Get all uncategorized transactions with optional pagination"""
        return self.db.get_uncategorized_transactions(limit, offset)

    def get_uncategorized_count(self):
        """Get count of uncategorized transactions"""
        return len(self.get_uncategorized_transactions())

    def classify_transaction(self, verifikationsnummer, category_name, confidence=None, classification_method=None):
        """Classify a transaction by verification number (for backward compatibility)"""
        # Efficient lookup using database index
        transaction = self.db.get_transaction_by_verification_number(verifikationsnummer)
        
        if transaction is None:
            raise ValueError(f"Transaction with verification number '{verifikationsnummer}' not found")
        
        return self.db.classify_transaction(transaction['id'], category_name, confidence, classification_method)

    def reclassify_transaction(self, transaction_id, category_name, confidence=None, classification_method=None):
        """Reclassify a transaction by transaction ID (direct database operation)"""
        return self.db.classify_transaction(transaction_id, category_name, confidence, classification_method)

    def get_unclassified_transactions(self):
        """Get transactions that have no category assigned (category_id IS NULL)"""
        c = self.db.conn.cursor()
        c.execute("SELECT verifikationsnummer, date, description, amount FROM transactions WHERE category_id IS NULL")
        return c.fetchall()

    # === Transaction Delete Functionality ===

    def delete_transaction(self, transaction_id):
        """Delete a single transaction by ID"""
        return self.db.delete_transaction(transaction_id)

    def delete_transactions_bulk(self, transaction_ids):
        """Delete multiple transactions by their IDs"""
        return self.db.delete_transactions_bulk(transaction_ids)

    # === CSV Import Functionality ===

    def import_csv(self, csv_path, csv_encoding='utf-8'):
        """Import transactions from CSV file"""
        df = None
        
        # Try different separator and encoding combinations
        for separator in [';', ',']:
            for encoding in [csv_encoding, 'latin-1']:
                try:
                    df_test = pd.read_csv(csv_path, sep=separator, encoding=encoding)
                    # Check if we got proper columns (more than 1 column suggests correct separator)
                    if len(df_test.columns) > 1:
                        df = df_test
                        break
                except (UnicodeDecodeError, Exception):
                    continue
            if df is not None:
                break
        
        if df is None:
            raise Exception("Could not read CSV file with any separator/encoding combination")

        # Convert to consistent column names
        column_mapping = {
            'Datum': 'Datum',
            'Date': 'Datum',
            'Bokföringsdatum': 'Datum',  # Swedish banking format
            'Beskrivning': 'Beskrivning', 
            'Description': 'Beskrivning',
            'Text': 'Beskrivning',  # Test format
            'Belopp': 'Belopp',
            'Amount': 'Belopp',
            'Verifikationsnummer': 'Verifikationsnummer',
            'Reference': 'Verifikationsnummer',
        }
        
        # Rename columns to standard names
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})

        # Check required columns exist
        required_columns = ['Datum', 'Beskrivning', 'Belopp']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Clean and process data
        df['Datum'] = pd.to_datetime(df['Datum'], errors='coerce')
        df = df.dropna(subset=['Datum'])
        df['Datum'] = df['Datum'].dt.strftime('%Y-%m-%d')
        
        # Convert amount to float, handling different formats
        if df['Belopp'].dtype == 'object':
            df['Belopp'] = df['Belopp'].str.replace(',', '.').str.replace(' ', '')
            df['Belopp'] = pd.to_numeric(df['Belopp'], errors='coerce')
        
        df = df.dropna(subset=['Belopp'])
        
        # Add year and month columns
        df['year'] = pd.to_datetime(df['Datum']).dt.year
        df['month'] = pd.to_datetime(df['Datum']).dt.month
        
        # Import to database
        self.db.import_transactions_bulk(df, "Uncategorized")
        
        # Auto-classify imported transactions using LLM-supported classification
        self._auto_classify_new_transactions(df)
        
        return len(df)
    
    def _auto_classify_new_transactions(self, df):
        """Automatically classify newly imported transactions using LLM-supported classification"""
        
        # Check if auto-classification is enabled
        auto_classify_enabled = os.getenv('AUTO_CLASSIFY_ON_IMPORT', 'true').lower() == 'true'
        if not auto_classify_enabled:
            self.logger.info("Automatic classification disabled by configuration")
            return
            
        try:
            # Import here to avoid circular imports
            from classifiers import AutoClassificationEngine
            
            # Initialize the auto-classification engine (includes LLM classifiers)
            engine = AutoClassificationEngine(self)
            
            # Get confidence threshold from environment
            confidence_threshold = float(os.getenv('AUTO_CLASSIFY_CONFIDENCE_THRESHOLD', '0.75'))
            
            # Auto-classify imported transactions
            classified_count, suggestions = engine.auto_classify_uncategorized(
                confidence_threshold=confidence_threshold,
                max_suggestions=len(df) * 2  # Allow processing all imported transactions
            )
            
            if classified_count > 0:
                self.logger.info(f"Auto-classified {classified_count} transactions using LLM-supported classification")
            
            # Log suggestions for review if any
            if suggestions:
                self.logger.info(f"{len(suggestions)} transactions have moderate confidence suggestions for manual review")
                
        except Exception as e:
            self.logger.warning(f"Auto-classification failed: {e}")
            # Don't fail the import if auto-classification fails

    # === Reporting Functionality ===
    
    def get_spending_report(self, year, month):
        """Get spending vs yearly budget report for a specific month"""
        return self.db.get_spending_report(year, month)
        
    def get_yearly_spending_report(self, year):
        """Get spending vs yearly budget report for entire year"""
        return self.db.get_yearly_spending_report(year)
    
    def generate_monthly_report(self, year, month):
        """Generate monthly report data for web API (alias for get_spending_report)"""
        return self.get_spending_report(year, month)
    
    def generate_yearly_report(self, year):
        """Generate yearly report data for web API (alias for get_yearly_spending_report)"""
        return self.get_yearly_spending_report(year)
