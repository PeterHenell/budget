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

    def get_classified_transactions_for_patterns(self):
        """Get classified transactions for building classification patterns"""
        return self.db.get_classified_transactions_for_patterns()

    def get_unclassified_transactions(self):
        """Get transactions that have no category assigned (category_id IS NULL)"""
        return self.db.get_unclassified_transactions()

    # === Transaction Delete Functionality ===

    def delete_transaction(self, transaction_id):
        """Delete a single transaction by ID"""
        return self.db.delete_transaction(transaction_id)

    def delete_transactions_bulk(self, transaction_ids):
        """Delete multiple transactions by their IDs"""
        return self.db.delete_transactions_bulk(transaction_ids)

    # === CSV Import Functionality ===

    def import_csv(self, csv_path, csv_encoding='utf-8', auto_classify=False):
        """Import transactions from CSV file with optional automatic classification"""
        try:
            # Step 1: Read and parse CSV file
            df = self._read_csv_with_fallback(csv_path, csv_encoding)
            
            # Step 2: Standardize column names
            df = self._standardize_csv_columns(df)
            
            # Step 3: Validate required columns
            self._validate_csv_columns(df)
            
            # Step 4: Clean and process data
            df = self._clean_csv_data(df)
            
            # Step 5: Import to database
            self.db.import_transactions_bulk(df, "Uncategorized")
            
            # Step 6: Auto-classify imported transactions (only if explicitly requested)
            if auto_classify:
                self._auto_classify_new_transactions(df)
            
            self.logger.info(f"Successfully imported {len(df)} transactions from {csv_path}")
            return len(df)
            
        except Exception as e:
            self.logger.error(f"Failed to import CSV file {csv_path}: {e}")
            raise

    def _read_csv_with_fallback(self, csv_path, csv_encoding):
        """Read CSV file with fallback for different separators and encodings"""
        df = None
        separators = [';', ',']
        encodings = [csv_encoding, 'latin-1']
        
        for separator in separators:
            for encoding in encodings:
                try:
                    df_test = pd.read_csv(csv_path, sep=separator, encoding=encoding)
                    # Check if we got proper columns (more than 1 column suggests correct separator)
                    if len(df_test.columns) > 1:
                        self.logger.debug(f"Successfully read CSV with separator='{separator}', encoding='{encoding}'")
                        return df_test
                except (UnicodeDecodeError, Exception) as e:
                    self.logger.debug(f"Failed to read CSV with separator='{separator}', encoding='{encoding}': {e}")
                    continue
        
        raise Exception("Could not read CSV file with any separator/encoding combination")

    def _standardize_csv_columns(self, df):
        """Standardize CSV column names to consistent format"""
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
        
        self.logger.debug(f"Standardized columns: {list(df.columns)}")
        return df

    def _validate_csv_columns(self, df):
        """Validate that required columns exist in the CSV"""
        required_columns = ['Datum', 'Beskrivning', 'Belopp']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}. Available columns: {list(df.columns)}")
        
        self.logger.debug(f"CSV validation passed - all required columns present")

    def _clean_csv_data(self, df):
        """Clean and process CSV data for database import"""
        original_count = len(df)
        
        # Clean date column
        df = self._clean_date_column(df)
        
        # Clean amount column
        df = self._clean_amount_column(df)
        
        # Add derived columns
        df = self._add_derived_columns(df)
        
        cleaned_count = len(df)
        if cleaned_count < original_count:
            self.logger.warning(f"Cleaned data: {original_count} -> {cleaned_count} rows ({original_count - cleaned_count} rows removed)")
        
        return df

    def _clean_date_column(self, df):
        """Clean and validate the date column, removing invalid dates"""
        try:
            # Create a copy to avoid SettingWithCopyWarning
            df = df.copy()
            
            # Convert to datetime, coercing invalid dates to NaT (Not a Time)
            df['Datum'] = pd.to_datetime(df['Datum'], errors='coerce')
            
            # Remove rows with invalid dates (NaT values)
            df = df.dropna(subset=['Datum'])
            
            # Convert back to string format for database storage
            df['Datum'] = df['Datum'].dt.strftime('%Y-%m-%d')
            
            return df
        except Exception as e:
            raise ValueError(f"Error cleaning date column: {str(e)}")
    
    def _clean_amount_column(self, df):
        """Clean and standardize amount column"""
        # Convert amount to float, handling different formats
        if df['Belopp'].dtype == 'object':
            # Handle European number format (comma as decimal separator)
            df['Belopp'] = df['Belopp'].str.replace(',', '.').str.replace(' ', '')
            df['Belopp'] = pd.to_numeric(df['Belopp'], errors='coerce')
        
        # Remove rows with invalid amounts
        invalid_amounts = df['Belopp'].isna().sum()
        if invalid_amounts > 0:
            self.logger.warning(f"Removing {invalid_amounts} rows with invalid amounts")
            
        df = df.dropna(subset=['Belopp'])
        
        return df

    def _add_derived_columns(self, df):
        """Add derived columns for year and month"""
        df['year'] = pd.to_datetime(df['Datum']).dt.year
        df['month'] = pd.to_datetime(df['Datum']).dt.month
        
        return df
    
    def _auto_classify_new_transactions(self, df):
        """Automatically classify newly imported transactions using LLM-supported classification"""
        
        # Check if auto-classification is enabled
        if not self._is_auto_classification_enabled():
            return
            
        try:
            # Get classification parameters
            engine = self._initialize_classification_engine()
            confidence_threshold = self._get_confidence_threshold()
            
            # Perform auto-classification
            classified_count, suggestions = engine.auto_classify_uncategorized(
                confidence_threshold=confidence_threshold,
                max_suggestions=len(df) * 2  # Allow processing all imported transactions
            )
            
            # Log results
            self._log_classification_results(classified_count, suggestions)
                
        except Exception as e:
            self.logger.warning(f"Auto-classification failed: {e}")
            # Don't fail the import if auto-classification fails

    def auto_classify_uncategorized(self, progress_callback=None):
        """
        Manually trigger auto-classification of uncategorized transactions
        Returns (classified_count, total_count)
        """
        try:
            # Get classification parameters
            engine = self._initialize_classification_engine()
            confidence_threshold = self._get_confidence_threshold()
            
            # Get uncategorized transactions for progress tracking
            uncategorized = self.get_uncategorized_transactions()
            total_count = len(uncategorized)
            
            if total_count == 0:
                self.logger.info("No uncategorized transactions found")
                return 0, 0
            
            self.logger.info(f"Starting auto-classification of {total_count} uncategorized transactions")
            
            # Perform auto-classification with progress callback
            classified_count, suggestions = engine.auto_classify_uncategorized(
                confidence_threshold=confidence_threshold,
                progress_callback=progress_callback
            )
            
            # Log results
            self._log_classification_results(classified_count, suggestions)
            
            return classified_count, total_count
                
        except Exception as e:
            self.logger.error(f"Manual auto-classification failed: {e}")
            raise

    def _is_auto_classification_enabled(self):
        """Check if automatic classification is enabled via configuration"""
        auto_classify_enabled = os.getenv('AUTO_CLASSIFY_ON_IMPORT', 'true').lower() == 'true'
        if not auto_classify_enabled:
            self.logger.info("Automatic classification disabled by configuration")
        return auto_classify_enabled

    def _initialize_classification_engine(self):
        """Initialize the auto-classification engine"""
        # Import here to avoid circular imports
        from classifiers import AutoClassificationEngine
        return AutoClassificationEngine(self)

    def _get_confidence_threshold(self):
        """Get confidence threshold from environment configuration"""
        return float(os.getenv('AUTO_CLASSIFY_CONFIDENCE_THRESHOLD', '0.75'))

    def _log_classification_results(self, classified_count, suggestions):
        """Log the results of auto-classification"""
        if classified_count > 0:
            self.logger.info(f"Auto-classified {classified_count} transactions using LLM-supported classification")
        
        if suggestions:
            self.logger.info(f"{len(suggestions)} transactions have moderate confidence suggestions for manual review")

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
