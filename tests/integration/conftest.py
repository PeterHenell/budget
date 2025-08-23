"""
Pytest Fixtures for Integration Tests
Provides user management and database setup as reusable fixtures
"""

import pytest
import sys
from pathlib import Path

# Add integration test directory to path
sys.path.insert(0, str(Path(__file__).parent))

from test_user_manager import IntegrationTestUserManager, get_test_connection_params
from robust_test_base import TestDatabaseManager


@pytest.fixture(scope="function")
def test_user_manager():
    """Provide test user manager with automatic cleanup"""
    connection_params = get_test_connection_params()
    manager = IntegrationTestUserManager(connection_params)
    
    try:
        manager.connect()
        yield manager
    finally:
        manager.cleanup_test_users()
        manager.close()


@pytest.fixture(scope="function")
def test_db_manager():
    """Provide test database manager"""
    connection_params = get_test_connection_params()
    manager = TestDatabaseManager(connection_params)
    
    try:
        manager.ensure_database_tables()
        yield manager
    finally:
        manager.clean_test_data()
        manager.close()


@pytest.fixture(scope="function")
def integration_users(test_user_manager):
    """Create integration test users and return their credentials"""
    return test_user_manager.setup_integration_test_users()


@pytest.fixture(scope="function")
def admin_session(integration_users):
    """Provide an authenticated admin session"""
    import requests
    
    base_url = "http://localhost:5000"
    admin_creds = integration_users['admin']
    
    session = requests.Session()
    login_data = {
        "username": admin_creds['username'],
        "password": admin_creds['password']
    }
    
    response = session.post(f"{base_url}/login", data=login_data, timeout=10)
    return session


@pytest.fixture(scope="function") 
def user_session(integration_users):
    """Provide an authenticated regular user session"""
    import requests
    
    base_url = "http://localhost:5000"
    user_creds = integration_users['user']
    
    session = requests.Session()
    login_data = {
        "username": user_creds['username'],
        "password": user_creds['password']
    }
    
    response = session.post(f"{base_url}/login", data=login_data, timeout=10)
    return session


@pytest.fixture(scope="function")
def wait_for_services():
    """Ensure services are ready before running tests"""
    import requests
    import time
    
    base_url = "http://localhost:5000"
    max_wait = 30
    
    print("⏳ Waiting for services to be ready...")
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code in [200, 503]:
                print("✓ Services are ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
    
    print("⚠ Services may not be fully ready, but continuing...")
    return False


@pytest.fixture(autouse=True, scope="session")
def ensure_containers_running():
    """Ensure Docker containers are running for all tests"""
    import subprocess
    import time
    
    try:
        # Check if containers are running
        result = subprocess.run([
            "docker", "compose", "ps", "--services", "--filter", "status=running"
        ], capture_output=True, text=True)
        
        running_services = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        if 'web' not in running_services or 'postgres' not in running_services:
            print("⚠ Some containers not running, attempting to start...")
            subprocess.run(["docker", "compose", "up", "-d"], check=False)
            time.sleep(5)
            
    except Exception as e:
        print(f"⚠ Container check warning: {e}")
