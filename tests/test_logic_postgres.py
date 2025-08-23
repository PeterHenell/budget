import unittest
import tempfile
import os
import sys
from pathlib import Path
import psycopg2
import time

# Add src directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from logic import BudgetLogic

class TestBudgetLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test database connection"""
        # Use test database configuration
        cls.test_connection_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'database': os.getenv('POSTGRES_TEST_DB', 'budget_test_db'),
            'user': os.getenv('POSTGRES_USER', 'budget_test_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'budget_test_password'),
            'port': os.getenv('POSTGRES_PORT', '5433')
        }
        
        # Create test database if it doesn't exist
        try:
            # Connect to default database to create test database
            default_params = cls.test_connection_params.copy()
            default_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**default_params)
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Check if test database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", 
                          (cls.test_connection_params['database'],))
            if not cursor.fetchone():
                cursor.execute(f"CREATE DATABASE {cls.test_connection_params['database']}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"Warning: Could not set up test database: {e}")
            print("Falling back to main database - tests may interfere with data!")
            cls.test_connection_params['database'] = os.getenv('POSTGRES_DB', 'budget_db')

    def setUp(self):
        """Set up test logic instance and clean database"""
        self.logic = BudgetLogic(self.test_connection_params)
        
        # Clean up any existing test data
        self._clean_test_data()
        
        # Add a test category and set yearly budget
        self.logic.add_category('TestCat')
        self.logic.set_budget('TestCat', 2025, 12000)  # Yearly budget
    
    def tearDown(self):
        """Clean up after test"""
        try:
            self._clean_test_data()
            self.logic.close()
        except:
            pass  # Ignore cleanup errors

    def _clean_test_data(self):
        """Remove test data from database"""
        try:
            cursor = self.logic.conn.cursor()
            
            # Delete test transactions
            cursor.execute("DELETE FROM transactions WHERE description LIKE %s", ('%test%',))
            cursor.execute("DELETE FROM transactions WHERE description LIKE %s", ('%Test%',))
            cursor.execute("DELETE FROM transactions WHERE description LIKE %s", ('%Desc%',))
            
            # Delete test budgets
            cursor.execute("""
                DELETE FROM budgets WHERE category_id IN (
                    SELECT id FROM categories WHERE name LIKE 'TestCat%'
                )
            """)
            
            # Delete test categories (except default ones)
            default_categories = ["Mat", "Boende", "Transport", "Nöje", "Hälsa", "Övrigt", "Uncategorized"]
            placeholders = ','.join(['%s'] * len(default_categories))
            cursor.execute(f"""
                DELETE FROM categories 
                WHERE name LIKE 'TestCat%' 
                AND name NOT IN ({placeholders})
            """, default_categories)
            
            self.logic.conn.commit()
        except Exception as e:
            if self.logic.conn:
                self.logic.conn.rollback()
            print(f"Warning: Could not clean test data: {e}")

    def test_db_connection(self):
        self.assertIsNotNone(self.logic.conn)

    def test_category_management(self):
        cats = self.logic.get_categories()
        self.assertIn('TestCat', cats)
        self.logic.remove_category('TestCat')
        self.assertNotIn('TestCat', self.logic.get_categories())
        self.logic.add_category('TestCat')

    def test_budget_setting(self):
        self.logic.set_budget('TestCat', 2025, 15000)  # Yearly budget
        amt = self.logic.get_budget('TestCat', 2025)
        self.assertEqual(amt, 15000)

    def test_budget_overwrite(self):
        # Test that setting budget again overwrites previous value
        self.logic.set_budget('TestCat', 2025, 18000)  # New yearly budget
        amt = self.logic.get_budget('TestCat', 2025)
        self.assertEqual(amt, 18000)

    def test_multiple_budgets_same_category(self):
        # Test setting budgets for same category but different years
        self.logic.set_budget('TestCat', 2024, 10000)
        self.logic.set_budget('TestCat', 2025, 15000)
        
        amt_2024 = self.logic.get_budget('TestCat', 2024)
        amt_2025 = self.logic.get_budget('TestCat', 2025)
        
        self.assertEqual(amt_2024, 10000)
        self.assertEqual(amt_2025, 15000)

    def test_import_multiple_transactions(self):
        import pandas as pd
        df = pd.DataFrame({
            'Verifikationsnummer': ['A1', 'A1', 'A2'],
            'Bokföringsdatum': ['2025-08-01', '2025-08-01', '2025-08-02'],
            'Text': ['Test Desc1', 'Test Desc1', 'Test Desc2'],
            'Belopp': [100, 100, 200]
        })
        test_csv = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        df.to_csv(test_csv.name, index=False, sep=';')
        test_csv.close()
        
        try:
            count = self.logic.import_csv(test_csv.name)
            self.assertEqual(count, 3)  # All 3 transactions imported
            
            # Transactions should now be in "Uncategorized" category, not unclassified
            unclassified = self.logic.get_unclassified_transactions()
            self.assertEqual(len(unclassified), 0)  # No unclassified transactions
            
            # But should be in uncategorized category
            uncategorized = self.logic.get_uncategorized_transactions()
            self.assertGreaterEqual(len(uncategorized), 3)  # At least our 3 transactions
        finally:
            os.remove(test_csv.name)

    def test_classification(self):
        self.logic.add_category('TestCat2')
        import pandas as pd
        df = pd.DataFrame({
            'Verifikationsnummer': ['B1'],
            'Bokföringsdatum': ['2025-08-03'],
            'Text': ['Test Desc3'],
            'Belopp': [300]
        })
        test_csv = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        df.to_csv(test_csv.name, index=False, sep=';')
        test_csv.close()
        
        try:
            self.logic.import_csv(test_csv.name)
            self.logic.classify_transaction('B1', 'TestCat2')
            txs = self.logic.get_unclassified_transactions()
            self.assertNotIn('B1', [tx[1] for tx in txs])  # Check verifikationsnummer not in unclassified
        finally:
            os.remove(test_csv.name)

    def test_spending_report(self):
        self.logic.add_category('TestCat3')
        self.logic.set_budget('TestCat3', 2025, 6000)  # Yearly budget
        import pandas as pd
        df = pd.DataFrame({
            'Verifikationsnummer': ['C1'],
            'Bokföringsdatum': ['2025-08-04'],
            'Text': ['Test Desc4'],
            'Belopp': [400]
        })
        test_csv = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        df.to_csv(test_csv.name, index=False, sep=';')
        test_csv.close()
        
        try:
            self.logic.import_csv(test_csv.name)
            self.logic.classify_transaction('C1', 'TestCat3')
            report = self.logic.get_spending_report(2025, 8)  # Monthly report
            
            # Find our test category in the report
            test_cat_report = None
            for item in report:
                if item['category'] == 'TestCat3':
                    test_cat_report = item
                    break
            
            self.assertIsNotNone(test_cat_report)
            self.assertEqual(test_cat_report['spent'], 400)
            self.assertEqual(test_cat_report['budget'], 6000)  # Yearly budget
            self.assertEqual(test_cat_report['diff'], 5600)  # 6000 - 400
        finally:
            os.remove(test_csv.name)

    def test_yearly_report(self):
        """Test yearly spending report"""
        self.logic.add_category('TestCat4')
        self.logic.set_budget('TestCat4', 2025, 12000)  # Yearly budget
        
        # Add transactions for different months
        import pandas as pd
        df = pd.DataFrame({
            'Verifikationsnummer': ['Y1', 'Y2', 'Y3'],
            'Bokföringsdatum': ['2025-01-15', '2025-06-20', '2025-12-10'],
            'Text': ['Test Jan expense', 'Test Jun expense', 'Test Dec expense'],
            'Belopp': [1000, 2000, 1500]
        })
        test_csv = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        df.to_csv(test_csv.name, index=False, sep=';')
        test_csv.close()
        
        try:
            self.logic.import_csv(test_csv.name)
            # Get uncategorized transactions (they will be in "Uncategorized" now)
            uncategorized = self.logic.get_uncategorized_transactions()
            # Reclassify all to TestCat4
            for tx in uncategorized:
                tx_id = tx[0]  # Transaction ID is first field in uncategorized results
                if any('Test' in str(field) for field in tx):  # Only reclassify our test transactions
                    self.logic.reclassify_transaction(tx_id, 'TestCat4')
            
            # Get yearly report
            report = self.logic.get_yearly_spending_report(2025)
            
            # Find our test category in the report
            test_cat_report = None
            for item in report:
                if item['category'] == 'TestCat4':
                    test_cat_report = item
                    break
            
            self.assertIsNotNone(test_cat_report)
            self.assertEqual(test_cat_report['spent'], 4500)  # 1000 + 2000 + 1500
            self.assertEqual(test_cat_report['budget'], 12000)
            self.assertEqual(test_cat_report['diff'], 7500)  # 12000 - 4500
        finally:
            os.remove(test_csv.name)

    def test_uncategorized_functionality(self):
        """Test the uncategorized transaction queue functionality"""
        import pandas as pd
        df = pd.DataFrame({
            'Verifikationsnummer': ['U1', 'U2'],
            'Bokföringsdatum': ['2025-08-01', '2025-08-02'],
            'Text': ['Test Uncategorized expense 1', 'Test Uncategorized expense 2'],
            'Belopp': [100, 200]
        })
        test_csv = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        df.to_csv(test_csv.name, index=False, sep=';')
        test_csv.close()
        
        try:
            # Import should put transactions in Uncategorized category
            count = self.logic.import_csv(test_csv.name)
            self.assertEqual(count, 2)
            
            # Check uncategorized count and transactions
            uncategorized_count = self.logic.get_uncategorized_count()
            self.assertGreaterEqual(uncategorized_count, 2)  # At least our 2 transactions
            
            uncategorized_txs = self.logic.get_uncategorized_transactions()
            self.assertGreaterEqual(len(uncategorized_txs), 2)
            
            # Find one of our test transactions
            test_tx_id = None
            for tx in uncategorized_txs:
                if 'Test Uncategorized' in str(tx[3]):  # Description is at index 3
                    test_tx_id = tx[0]  # Transaction ID
                    break
            
            self.assertIsNotNone(test_tx_id, "Could not find test transaction")
            
            # Reclassify one transaction
            self.logic.reclassify_transaction(test_tx_id, 'TestCat')
            
            # Check that count decreased
            new_count = self.logic.get_uncategorized_count()
            self.assertEqual(new_count, uncategorized_count - 1)
            
            # Check with pagination
            paginated_txs = self.logic.get_uncategorized_transactions(limit=1, offset=0)
            self.assertEqual(len(paginated_txs), 1)
        finally:
            os.remove(test_csv.name)

if __name__ == '__main__':
    unittest.main()
