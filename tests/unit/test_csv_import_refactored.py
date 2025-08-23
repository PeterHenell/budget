import unittest
import tempfile
import os
import sys
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from logic import BudgetLogic

class TestCSVImportRefactored(unittest.TestCase):
    """Test the refactored CSV import methods for method complexity improvements"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock database to avoid actual database operations during unit tests
        self.mock_db = Mock()
        self.logic = BudgetLogic.__new__(BudgetLogic)  # Create without calling __init__
        self.logic.db = self.mock_db
        self.logic.logger = Mock()
        
        # Create test CSV files
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def _create_test_csv(self, filename, content, encoding='utf-8'):
        """Helper method to create test CSV files"""
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w', encoding=encoding) as f:
            f.write(content)
        return filepath

    def test_read_csv_with_fallback_success_semicolon(self):
        """Test reading CSV with semicolon separator"""
        csv_content = "Datum;Beskrivning;Belopp\n2025-01-01;Test transaction;-100.50\n2025-01-02;Another test;200.00"
        csv_path = self._create_test_csv('test_semicolon.csv', csv_content)
        
        df = self.logic._read_csv_with_fallback(csv_path, 'utf-8')
        
        self.assertEqual(len(df), 2)
        self.assertIn('Datum', df.columns)
        self.assertIn('Beskrivning', df.columns)
        self.assertIn('Belopp', df.columns)

    def test_read_csv_with_fallback_success_comma(self):
        """Test reading CSV with comma separator"""
        csv_content = "Date,Description,Amount\n2025-01-01,Test transaction,-100.50\n2025-01-02,Another test,200.00"
        csv_path = self._create_test_csv('test_comma.csv', csv_content)
        
        df = self.logic._read_csv_with_fallback(csv_path, 'utf-8')
        
        self.assertEqual(len(df), 2)
        self.assertIn('Date', df.columns)
        self.assertIn('Description', df.columns)
        self.assertIn('Amount', df.columns)

    def test_read_csv_with_fallback_encoding_fallback(self):
        """Test reading CSV with encoding fallback"""
        # Create CSV with latin-1 specific characters
        csv_content = "Datum;Beskrivning;Belopp\n2025-01-01;Café transaction;-100.50"
        csv_path = self._create_test_csv('test_encoding.csv', csv_content, 'latin-1')
        
        # Should succeed with latin-1 fallback
        df = self.logic._read_csv_with_fallback(csv_path, 'utf-8')
        
        self.assertEqual(len(df), 1)
        self.assertIn('Café', df.iloc[0]['Beskrivning'])

    def test_read_csv_with_fallback_failure(self):
        """Test reading CSV that fails all combinations"""
        # Create an invalid CSV file
        csv_path = self._create_test_csv('invalid.csv', "invalid content without proper structure")
        
        with self.assertRaises(Exception) as context:
            self.logic._read_csv_with_fallback(csv_path, 'utf-8')
        
        self.assertIn("Could not read CSV file", str(context.exception))

    def test_standardize_csv_columns(self):
        """Test column name standardization"""
        # Create DataFrame with various column name formats
        test_data = {
            'Date': ['2025-01-01'],
            'Description': ['Test'],
            'Amount': [100.00],
            'Reference': ['REF123']
        }
        df = pd.DataFrame(test_data)
        
        result_df = self.logic._standardize_csv_columns(df)
        
        # Check that columns are renamed correctly
        expected_columns = ['Datum', 'Beskrivning', 'Belopp', 'Verifikationsnummer']
        for col in expected_columns:
            self.assertIn(col, result_df.columns)

    def test_standardize_csv_columns_swedish_format(self):
        """Test column standardization for Swedish banking format"""
        test_data = {
            'Bokföringsdatum': ['2025-01-01'],
            'Text': ['Swedish transaction'],
            'Belopp': [100.00]
        }
        df = pd.DataFrame(test_data)
        
        result_df = self.logic._standardize_csv_columns(df)
        
        self.assertIn('Datum', result_df.columns)
        self.assertIn('Beskrivning', result_df.columns)
        self.assertEqual(result_df.iloc[0]['Beskrivning'], 'Swedish transaction')

    def test_validate_csv_columns_success(self):
        """Test successful CSV column validation"""
        test_data = {
            'Datum': ['2025-01-01'],
            'Beskrivning': ['Test'],
            'Belopp': [100.00]
        }
        df = pd.DataFrame(test_data)
        
        # Should not raise exception
        try:
            self.logic._validate_csv_columns(df)
        except ValueError:
            self.fail("_validate_csv_columns raised ValueError unexpectedly")

    def test_validate_csv_columns_missing_columns(self):
        """Test CSV validation with missing required columns"""
        test_data = {
            'Datum': ['2025-01-01'],
            'Beskrivning': ['Test']
            # Missing 'Belopp' column
        }
        df = pd.DataFrame(test_data)
        
        with self.assertRaises(ValueError) as context:
            self.logic._validate_csv_columns(df)
        
        self.assertIn("Missing required columns", str(context.exception))
        self.assertIn("Belopp", str(context.exception))

    def test_clean_date_column(self):
        """Test date column cleaning"""
        test_data = {
            'Datum': ['2025-01-01', '2025-13-45', '2025-01-02', 'invalid-date', '2025-01-03'],
            'other': [1, 2, 3, 4, 5]
        }
        df = pd.DataFrame(test_data)
        
        result_df = self.logic._clean_date_column(df)
        
        # Should have 3 valid rows (invalid dates removed)
        self.assertEqual(len(result_df), 3)
        # Check date format
        self.assertEqual(result_df.iloc[0]['Datum'], '2025-01-01')

    def test_clean_amount_column_string_format(self):
        """Test amount column cleaning with European number format"""
        test_data = {
            'Belopp': ['100,50', '200,00', 'invalid', '300.25', ''],
            'other': [1, 2, 3, 4, 5]
        }
        df = pd.DataFrame(test_data)
        
        result_df = self.logic._clean_amount_column(df)
        
        # Should have 3 valid rows (invalid and empty removed)
        self.assertEqual(len(result_df), 3)
        # Check comma to dot conversion
        self.assertEqual(result_df.iloc[0]['Belopp'], 100.50)
        self.assertEqual(result_df.iloc[1]['Belopp'], 200.00)

    def test_clean_amount_column_numeric_format(self):
        """Test amount column cleaning with already numeric data"""
        test_data = {
            'Belopp': [100.50, 200.00, float('nan'), 300.25],
            'other': [1, 2, 3, 4]
        }
        df = pd.DataFrame(test_data)
        
        result_df = self.logic._clean_amount_column(df)
        
        # Should have 3 valid rows (NaN removed)
        self.assertEqual(len(result_df), 3)
        self.assertEqual(result_df.iloc[0]['Belopp'], 100.50)

    def test_add_derived_columns(self):
        """Test adding year and month columns"""
        test_data = {
            'Datum': ['2025-01-15', '2025-12-31'],
            'other': [1, 2]
        }
        df = pd.DataFrame(test_data)
        
        result_df = self.logic._add_derived_columns(df)
        
        self.assertIn('year', result_df.columns)
        self.assertIn('month', result_df.columns)
        self.assertEqual(result_df.iloc[0]['year'], 2025)
        self.assertEqual(result_df.iloc[0]['month'], 1)
        self.assertEqual(result_df.iloc[1]['month'], 12)

    @patch.dict(os.environ, {'AUTO_CLASSIFY_ON_IMPORT': 'false'})
    def test_is_auto_classification_disabled(self):
        """Test auto-classification when disabled by configuration"""
        result = self.logic._is_auto_classification_enabled()
        
        self.assertFalse(result)
        self.logic.logger.info.assert_called_with("Automatic classification disabled by configuration")

    @patch.dict(os.environ, {'AUTO_CLASSIFY_ON_IMPORT': 'true'})
    def test_is_auto_classification_enabled(self):
        """Test auto-classification when enabled by configuration"""
        result = self.logic._is_auto_classification_enabled()
        
        self.assertTrue(result)

    @patch.dict(os.environ, {'AUTO_CLASSIFY_CONFIDENCE_THRESHOLD': '0.85'})
    def test_get_confidence_threshold_custom(self):
        """Test getting custom confidence threshold from environment"""
        threshold = self.logic._get_confidence_threshold()
        
        self.assertEqual(threshold, 0.85)

    def test_get_confidence_threshold_default(self):
        """Test getting default confidence threshold"""
        # Remove environment variable if present
        if 'AUTO_CLASSIFY_CONFIDENCE_THRESHOLD' in os.environ:
            del os.environ['AUTO_CLASSIFY_CONFIDENCE_THRESHOLD']
        
        threshold = self.logic._get_confidence_threshold()
        
        self.assertEqual(threshold, 0.75)

    def test_log_classification_results_success(self):
        """Test logging classification results with successes"""
        self.logic._log_classification_results(5, ['suggestion1', 'suggestion2'])
        
        self.logic.logger.info.assert_any_call("Auto-classified 5 transactions using LLM-supported classification")
        self.logic.logger.info.assert_any_call("2 transactions have moderate confidence suggestions for manual review")

    def test_log_classification_results_no_success(self):
        """Test logging classification results with no successes"""
        self.logic._log_classification_results(0, [])
        
        # Should not log anything for zero results
        self.logic.logger.info.assert_not_called()

    @patch('logic.BudgetLogic._is_auto_classification_enabled')
    def test_auto_classify_disabled(self, mock_enabled):
        """Test auto-classification when disabled"""
        mock_enabled.return_value = False
        
        df = pd.DataFrame({'Datum': ['2025-01-01'], 'Beskrivning': ['Test'], 'Belopp': [100]})
        
        self.logic._auto_classify_new_transactions(df)
        
        # Should return early without attempting classification
        mock_enabled.assert_called_once()

    @patch('logic.BudgetLogic._log_classification_results')
    @patch('logic.BudgetLogic._get_confidence_threshold')
    @patch('logic.BudgetLogic._initialize_classification_engine')
    @patch('logic.BudgetLogic._is_auto_classification_enabled')
    def test_auto_classify_success(self, mock_enabled, mock_engine_init, mock_threshold, mock_log):
        """Test successful auto-classification"""
        # Setup mocks
        mock_enabled.return_value = True
        mock_threshold.return_value = 0.75
        mock_engine = Mock()
        mock_engine.auto_classify_uncategorized.return_value = (3, ['suggestion1'])
        mock_engine_init.return_value = mock_engine
        
        df = pd.DataFrame({'Datum': ['2025-01-01'], 'Beskrivning': ['Test'], 'Belopp': [100]})
        
        self.logic._auto_classify_new_transactions(df)
        
        # Verify all steps were called
        mock_enabled.assert_called_once()
        mock_engine_init.assert_called_once()
        mock_threshold.assert_called_once()
        mock_engine.auto_classify_uncategorized.assert_called_once_with(
            confidence_threshold=0.75,
            max_suggestions=2  # len(df) * 2
        )
        mock_log.assert_called_once_with(3, ['suggestion1'])

    @patch('logic.BudgetLogic._initialize_classification_engine')
    @patch('logic.BudgetLogic._is_auto_classification_enabled')
    def test_auto_classify_exception_handling(self, mock_enabled, mock_engine_init):
        """Test auto-classification exception handling"""
        # Setup mocks to raise exception
        mock_enabled.return_value = True
        mock_engine_init.side_effect = Exception("Classification engine failed")
        
        df = pd.DataFrame({'Datum': ['2025-01-01'], 'Beskrivning': ['Test'], 'Belopp': [100]})
        
        # Should not raise exception, but log warning
        try:
            self.logic._auto_classify_new_transactions(df)
        except Exception:
            self.fail("_auto_classify_new_transactions should handle exceptions gracefully")
        
        # Verify warning was logged
        self.logic.logger.warning.assert_called_with("Auto-classification failed: Classification engine failed")


class TestCSVImportIntegration(unittest.TestCase):
    """Integration tests for the full CSV import process"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db = Mock()
        self.logic = BudgetLogic.__new__(BudgetLogic)
        self.logic.db = self.mock_db
        self.logic.logger = Mock()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def _create_test_csv(self, filename, content, encoding='utf-8'):
        """Helper method to create test CSV files"""
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w', encoding=encoding) as f:
            f.write(content)
        return filepath

    @patch('logic.BudgetLogic._auto_classify_new_transactions')
    def test_import_csv_full_process_success(self, mock_auto_classify):
        """Test full CSV import process with valid data"""
        csv_content = "Date;Description;Amount\n2025-01-01;Test transaction;-100.50\n2025-01-02;Another test;200.00"
        csv_path = self._create_test_csv('valid.csv', csv_content)
        
        result = self.logic.import_csv(csv_path)
        
        # Verify result
        self.assertEqual(result, 2)
        
        # Verify database import was called
        self.mock_db.import_transactions_bulk.assert_called_once()
        
        # Verify auto-classification was attempted
        mock_auto_classify.assert_called_once()
        
        # Verify logging
        self.logic.logger.info.assert_called()

    def test_import_csv_invalid_file(self):
        """Test CSV import with invalid file"""
        csv_path = self._create_test_csv('invalid.csv', "not a valid csv")
        
        with self.assertRaises(Exception):
            self.logic.import_csv(csv_path)
        
        # Verify error was logged
        self.logic.logger.error.assert_called()


if __name__ == '__main__':
    unittest.main()
