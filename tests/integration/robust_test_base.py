"""
Robust Integration Test Base Classes
Provides user management, database setup, and cleanup for integration tests
"""

import pytest
import requests
import time
import subprocess
import os
import psycopg2
from typing import Dict, Any, Optional
from test_user_manager import IntegrationTestUserManager, get_test_connection_params


class TestDatabaseManager:
    """Manages test database setup and cleanup"""
    
    def __init__(self, connection_params: Dict[str, Any]):
        self.connection_params = connection_params
        self.conn = None
        
    def connect(self):
        """Connect to database"""
        if self.conn is None:
            self.conn = psycopg2.connect(**self.connection_params)
            self.conn.autocommit = True
            
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            
    def ensure_database_tables(self):
        """Ensure all required tables exist"""
        try:
            self.connect()
            
            # Import and run database initialization
            import sys
            sys.path.insert(0, '/app/src')
            from init_database import DatabaseInitializer
            
            # Initialize database without admin user (we'll create test users separately)
            initializer = DatabaseInitializer(self.connection_params)
            initializer.connect()
            
            try:
                initializer.create_tables()
                initializer.create_indexes()
                initializer.insert_default_categories()
                print("✓ Database tables ensured")
            finally:
                initializer.close()
                
        except Exception as e:
            print(f"⚠ Database initialization warning: {e}")
            
    def clean_test_data(self):
        """Clean up test data from database"""
        try:
            self.connect()
            c = self.conn.cursor()
            
            # Clean up test data in proper order (respecting foreign keys)
            cleanup_tables = [
                'transactions', 
                'budgets'
            ]
            
            for table in cleanup_tables:
                try:
                    # Only clean up obvious test data
                    if table == 'transactions':
                        c.execute("DELETE FROM transactions WHERE description LIKE '%TEST%' OR description LIKE '%test%'")
                    elif table == 'budgets':
                        c.execute("DELETE FROM budgets WHERE amount < 0")  # Negative amounts are likely test data
                        
                    deleted = c.rowcount
                    if deleted > 0:
                        print(f"  ✓ Cleaned {deleted} records from {table}")
                except psycopg2.Error as e:
                    print(f"  ⚠ Error cleaning {table}: {e}")
                    
            print("✓ Test data cleanup completed")
            
        except Exception as e:
            print(f"⚠ Test data cleanup error: {e}")


class RobustIntegrationTestBase:
    """
    Robust base class for integration tests with proper user and database management
    """
    
    # Test configuration
    BASE_URL = "http://localhost:5000"  # Using main containers, not separate test containers
    
    def setup_method(self, method):
        """Setup method called before each test method"""
        print(f"\n🔧 Setting up test: {method.__name__}")
        
        # Initialize connection parameters and managers
        self.connection_params = get_test_connection_params()
        self.user_manager = IntegrationTestUserManager(self.connection_params)
        self.db_manager = TestDatabaseManager(self.connection_params)
        self.test_users = {}
        
        # Ensure database is properly set up
        self.db_manager.ensure_database_tables()
        
        # Set up test users
        self.test_users = self.user_manager.setup_integration_test_users()
        
        # Wait for services to be ready
        self._wait_for_services()
        
    def teardown_method(self, method):
        """Cleanup method called after each test method"""
        print(f"\n🧹 Cleaning up test: {method.__name__}")
        
        if self.db_manager:
            self.db_manager.clean_test_data()
            self.db_manager.close()
            
        if self.user_manager:
            self.user_manager.cleanup_test_users()
            self.user_manager.close()
            
    @classmethod
    def setup_class(cls):
        """Setup method called once per test class"""
        print(f"\n🚀 Setting up test class: {cls.__name__}")
        
        # Ensure containers are running (but don't start new ones)
        cls._ensure_containers_running()
        
    @classmethod
    def teardown_class(cls):
        """Cleanup method called once per test class"""
        print(f"\n🏁 Test class completed: {cls.__name__}")
        
        # Reset test environment completely
        connection_params = get_test_connection_params()
        user_manager = IntegrationTestUserManager(connection_params)
        try:
            user_manager.reset_test_environment()
        finally:
            user_manager.close()
    
    @classmethod
    def _ensure_containers_running(cls):
        """Ensure Docker containers are running"""
        try:
            # Check if containers are already running
            result = subprocess.run([
                "docker", "compose", "ps", "--services", "--filter", "status=running"
            ], capture_output=True, text=True)
            
            running_services = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            if 'web' not in running_services or 'postgres' not in running_services:
                print("⚠ Some containers not running, attempting to start...")
                subprocess.run([
                    "docker", "compose", "up", "-d"
                ], check=False)
                time.sleep(5)  # Give containers time to start
                
        except Exception as e:
            print(f"⚠ Container check warning: {e}")
            
    def _wait_for_services(self, max_wait: int = 30):
        """Wait for web services to be ready"""
        print("⏳ Waiting for services to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(f"{self.BASE_URL}/health", timeout=5)
                if response.status_code in [200, 503]:  # 503 might indicate service issues but it's responding
                    print("✓ Services are ready!")
                    return
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(2)
        
        print("⚠ Services may not be fully ready, but continuing with tests...")
    
    def get_authenticated_session(self, user_type: str = 'admin') -> requests.Session:
        """
        Get an authenticated session for testing
        
        Args:
            user_type: Type of user ('admin', 'user', 'compat_admin')
            
        Returns:
            Authenticated requests session
        """
        if user_type not in self.test_users:
            raise ValueError(f"User type '{user_type}' not available. Available types: {list(self.test_users.keys())}")
            
        user_creds = self.test_users[user_type]
        session = requests.Session()
        
        # Login
        login_data = {
            "username": user_creds['username'],
            "password": user_creds['password']
        }
        
        try:
            response = session.post(f"{self.BASE_URL}/login", data=login_data, timeout=10)
            
            # Check if login was successful (should redirect to dashboard or return 200)
            if response.status_code not in [200, 302]:
                print(f"⚠ Login may have failed: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
            
            return session
            
        except Exception as e:
            print(f"⚠ Authentication error for {user_type}: {e}")
            return session
    
    def create_test_transaction_data(self) -> Dict[str, Any]:
        """Create sample transaction data for testing"""
        return {
            'verifikationsnummer': 'TEST001',
            'date': '2025-08-23',
            'description': 'TEST TRANSACTION FOR INTEGRATION',
            'amount': -100.50,
            'year': 2025,
            'month': 8
        }
        
    def ensure_test_category(self, category_name: str = "TEST_CATEGORY") -> bool:
        """Ensure a test category exists"""
        try:
            self.db_manager.connect()
            c = self.db_manager.conn.cursor()
            
            # Check if category exists
            c.execute("SELECT COUNT(*) FROM categories WHERE name = %s", (category_name,))
            if c.fetchone()[0] == 0:
                c.execute("INSERT INTO categories (name) VALUES (%s)", (category_name,))
                print(f"  ✓ Created test category: {category_name}")
            
            return True
        except Exception as e:
            print(f"  ⚠ Error creating test category: {e}")
            return False


class QuickIntegrationTestBase(RobustIntegrationTestBase):
    """
    Lighter version for tests that don't need full database setup
    """
    
    def setup_method(self, method):
        """Lighter setup - just ensure users exist"""
        print(f"\n🔧 Quick setup: {method.__name__}")
        
        # Initialize connection parameters
        self.connection_params = get_test_connection_params()
        self.user_manager = IntegrationTestUserManager(self.connection_params) 
        
        # Only create users, don't wait for all services
        self.test_users = self.user_manager.setup_integration_test_users()


# Utility functions for tests
def skip_if_no_docker():
    """Skip test if Docker is not available"""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True)
        if result.returncode != 0:
            return pytest.mark.skip(reason="Docker not available")
    except FileNotFoundError:
        return pytest.mark.skip(reason="Docker not installed")
    return lambda x: x


def skip_if_containers_not_running():
    """Skip test if containers are not running"""
    try:
        result = subprocess.run([
            "docker", "compose", "ps", "--services", "--filter", "status=running"
        ], capture_output=True, text=True)
        
        running_services = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        if 'web' not in running_services or 'postgres' not in running_services:
            return pytest.mark.skip(reason="Required containers not running")
    except Exception:
        return pytest.mark.skip(reason="Cannot check container status")
    return lambda x: x
