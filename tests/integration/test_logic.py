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
    """Test BudgetLogic with PostgreSQL backend"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database connection"""
        # Use test database configuration
        cls.test_connection_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'database': os.getenv('POSTGRES_TEST_DB', 'budget_test_db'),
            'user': os.getenv('POSTGRES_USER', 'budget_test_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'budget_test_password'),
            'port': os.getenv('POSTGRES_PORT', '5433')  # Test database port
        }
        
        # Wait for database to be ready
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                test_conn = psycopg2.connect(**cls.test_connection_params)
                test_conn.close()
                break
            except psycopg2.Error:
                if attempt == max_attempts - 1:
                    raise
                print(f"Waiting for test database... (attempt {attempt + 1})")
                time.sleep(1)
        
    def setUp(self):
        """Set up test data"""
        self.logic = BudgetLogic(self.test_connection_params)
        
        # Clean up any existing test data
        try:
            self.logic.remove_category('TestCat')
            self.logic.remove_category('TestCat2')
            self.logic.remove_category('TestCat3')
            self.logic.remove_category('TestCat4')
        except:
            pass
        
        # Clean up any test transactions (simple approach - remove by verifikationsnummer patterns)
        try:
            cursor = self.logic.conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE verifikationsnummer LIKE 'TEST%' OR verifikationsnummer LIKE 'T%' OR verifikationsnummer LIKE 'U%' OR verifikationsnummer LIKE 'Y%'")
            self.logic.conn.commit()
        except:
            pass
            
        # Add a test category and set yearly budget
        self.logic.add_category('TestCat')
        self.logic.set_budget('TestCat', 2025, 12000)  # Yearly budget
    
    def tearDown(self):
        """Clean up test data"""
        try:
            # Clean up test transactions
            cursor = self.logic.conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE verifikationsnummer LIKE 'TEST%' OR verifikationsnummer LIKE 'T%' OR verifikationsnummer LIKE 'U%' OR verifikationsnummer LIKE 'Y%'")
            self.logic.conn.commit()
            
            # Clean up test categories
            self.logic.remove_category('TestCat')
            self.logic.remove_category('TestCat2')
            self.logic.remove_category('TestCat3')
            self.logic.remove_category('TestCat4')
        except:
            pass
        self.logic.close()

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

    def test_import_multiple_transactions(self):
        import pandas as pd
        df = pd.DataFrame({
            'Verifikationsnummer': ['A1', 'A1', 'A2'],
            'Bokföringsdatum': ['2025-08-01', '2025-08-01', '2025-08-02'],
            'Text': ['Desc1', 'Desc1', 'Desc2'],
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
            
            # Check uncategorized transactions instead
            uncategorized = self.logic.get_uncategorized_transactions()
            self.assertEqual(len(uncategorized), 3)  # All in "Uncategorized" category
        finally:
            os.remove(test_csv.name)

    def test_classification(self):
        self.logic.add_category('TestCat2')
        import pandas as pd
        df = pd.DataFrame({
            'Verifikationsnummer': ['B1'],
            'Bokföringsdatum': ['2025-08-03'],
            'Text': ['Desc3'],
            'Belopp': [300]
        })
        test_csv = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        df.to_csv(test_csv.name, index=False, sep=';')
        test_csv.close()
        
        try:
            self.logic.import_csv(test_csv.name)
            self.logic.classify_transaction('B1', 'TestCat2')
            txs = self.logic.get_unclassified_transactions()
            self.assertNotIn('B1', [tx[0] for tx in txs])
        finally:
            os.remove(test_csv.name)

    def test_spending_report(self):
        self.logic.add_category('TestCat3')
        self.logic.set_budget('TestCat3', 2025, 6000)  # Yearly budget
        import pandas as pd
        df = pd.DataFrame({
            'Verifikationsnummer': ['C1'],
            'Bokföringsdatum': ['2025-08-04'],
            'Text': ['Desc4'],
            'Belopp': [400]
        })
        test_csv = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        df.to_csv(test_csv.name, index=False, sep=';')
        test_csv.close()
        
        try:
            self.logic.import_csv(test_csv.name)
            self.logic.classify_transaction('C1', 'TestCat3')
            report = self.logic.get_spending_report(2025, 8)  # Monthly report
            found = False
            for row in report:
                if row['category'] == 'TestCat3':
                    self.assertEqual(row['spent'], 400)  # Spent in August
                    self.assertEqual(row['budget'], 6000)  # Yearly budget
                    found = True
            self.assertTrue(found)
        finally:
            os.remove(test_csv.name)

    def test_multiple_budgets_same_category(self):
        """Test setting budgets for same category across different years"""
        self.logic.set_budget('TestCat', 2025, 12000)
        self.logic.set_budget('TestCat', 2026, 15000)
        self.logic.set_budget('TestCat', 2027, 10000)
        
        # Verify each year has correct budget
        self.assertEqual(self.logic.get_budget('TestCat', 2025), 12000)
        self.assertEqual(self.logic.get_budget('TestCat', 2026), 15000) 
        self.assertEqual(self.logic.get_budget('TestCat', 2027), 10000)
        
    def test_budget_overwrite(self):
        """Test that setting budget for same category/year overwrites previous"""
        self.logic.set_budget('TestCat', 2025, 12000)
        self.logic.set_budget('TestCat', 2025, 18000)  # Overwrite
        
        self.assertEqual(self.logic.get_budget('TestCat', 2025), 18000)
        
    def test_yearly_report(self):
        """Test yearly spending report"""
        self.logic.add_category('TestCat4')
        self.logic.set_budget('TestCat4', 2025, 12000)  # Yearly budget
        
        # Add transactions for different months
        import pandas as pd
        df = pd.DataFrame({
            'Verifikationsnummer': ['Y1', 'Y2', 'Y3'],
            'Bokföringsdatum': ['2025-01-15', '2025-06-20', '2025-12-10'],
            'Text': ['Jan expense', 'Jun expense', 'Dec expense'],
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
                self.logic.reclassify_transaction(tx_id, 'TestCat4')
            
            # Get yearly report
            report = self.logic.get_yearly_spending_report(2025)
            found = False
            for row in report:
                if row['category'] == 'TestCat4':
                    self.assertEqual(row['spent'], 4500)  # Total spending across year
                    self.assertEqual(row['budget'], 12000)  # Yearly budget
                    found = True
            self.assertTrue(found)
        finally:
            os.remove(test_csv.name)

    def test_uncategorized_functionality(self):
        """Test the uncategorized transaction queue functionality"""
        import pandas as pd
        df = pd.DataFrame({
            'Verifikationsnummer': ['U1', 'U2'],
            'Bokföringsdatum': ['2025-08-01', '2025-08-02'],
            'Text': ['Uncategorized expense 1', 'Uncategorized expense 2'],
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
            self.assertEqual(uncategorized_count, 2)
            
            uncategorized_txs = self.logic.get_uncategorized_transactions()
            self.assertEqual(len(uncategorized_txs), 2)
            
            # Reclassify one transaction
            tx_id = uncategorized_txs[0][0]  # Get first transaction ID
            self.logic.reclassify_transaction(tx_id, 'TestCat')
            
            # Check that count decreased
            new_count = self.logic.get_uncategorized_count()
            self.assertEqual(new_count, 1)
            
            # Check with pagination
            paginated_txs = self.logic.get_uncategorized_transactions(limit=1, offset=0)
            self.assertEqual(len(paginated_txs), 1)
            
        finally:
            os.remove(test_csv.name)

if __name__ == "__main__":
    unittest.main()
