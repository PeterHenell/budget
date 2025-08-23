"""
Test User Management Utility
Provides robust user creation and cleanup for integration tests
"""

import os
import psycopg2
import psycopg2.extras
from typing import Dict, List, Optional, Any
import secrets
import string
from contextlib import contextmanager


class IntegrationTestUserManager:
    """Manages test users for integration tests with proper cleanup"""
    
    def __init__(self, connection_params: Dict[str, Any]):
        """
        Initialize test user manager
        
        Args:
            connection_params: Database connection parameters
        """
        self.connection_params = connection_params
        self.created_users = set()  # Track users created during tests
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
            
    @contextmanager
    def database_connection(self):
        """Context manager for database connections"""
        try:
            self.connect()
            yield self.conn
        finally:
            pass  # Don't close connection here as it might be reused
    
    def generate_test_password(self, length: int = 12) -> str:
        """Generate a secure test password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def create_test_user(self, username: str, password: str = None, role: str = 'user', 
                        cleanup: bool = True) -> Dict[str, str]:
        """
        Create a test user with proper tracking for cleanup
        
        Args:
            username: Username for the test user
            password: Password (will generate secure one if not provided)
            role: User role ('user' or 'admin')
            cleanup: Whether to track this user for cleanup
            
        Returns:
            Dict with username and password
            
        Raises:
            Exception: If user creation fails
        """
        if password is None:
            password = self.generate_test_password()
            
        try:
            import bcrypt
        except ImportError:
            raise Exception("bcrypt is required for user creation but not installed")
            
        with self.database_connection():
            try:
                c = self.conn.cursor()
                
                # Check if user already exists
                c.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
                if c.fetchone()[0] > 0:
                    if cleanup:
                        # User exists, we'll track it for cleanup
                        self.created_users.add(username)
                    return {'username': username, 'password': password}
                
                # Create password hash
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                # Insert user
                c.execute("""
                    INSERT INTO users (username, password_hash, role, is_active) 
                    VALUES (%s, %s, %s, TRUE)
                """, (username, password_hash, role))
                
                if cleanup:
                    self.created_users.add(username)
                
                return {'username': username, 'password': password}
                
            except psycopg2.Error as e:
                raise Exception(f"Failed to create test user {username}: {e}")
    
    def ensure_admin_user(self, username: str = "test_admin", password: str = None) -> Dict[str, str]:
        """
        Ensure an admin user exists for testing
        
        Args:
            username: Admin username
            password: Admin password (will generate if not provided)
            
        Returns:
            Dict with username and password
        """
        return self.create_test_user(username, password, role='admin', cleanup=True)
    
    def ensure_regular_user(self, username: str = "test_user", password: str = None) -> Dict[str, str]:
        """
        Ensure a regular user exists for testing
        
        Args:
            username: Regular user username
            password: User password (will generate if not provided)
            
        Returns:
            Dict with username and password
        """
        return self.create_test_user(username, password, role='user', cleanup=True)
    
    def user_exists(self, username: str) -> bool:
        """Check if a user exists in the database"""
        with self.database_connection():
            try:
                c = self.conn.cursor()
                c.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
                return c.fetchone()[0] > 0
            except psycopg2.Error:
                return False
    
    def get_user_role(self, username: str) -> Optional[str]:
        """Get the role of a user"""
        with self.database_connection():
            try:
                c = self.conn.cursor()
                c.execute("SELECT role FROM users WHERE username = %s", (username,))
                result = c.fetchone()
                return result[0] if result else None
            except psycopg2.Error:
                return None
    
    def delete_user(self, username: str) -> bool:
        """
        Delete a user from the database
        
        Args:
            username: Username to delete
            
        Returns:
            True if user was deleted, False otherwise
        """
        with self.database_connection():
            try:
                c = self.conn.cursor()
                c.execute("DELETE FROM users WHERE username = %s", (username,))
                deleted = c.rowcount > 0
                
                # Remove from tracking set
                self.created_users.discard(username)
                
                return deleted
            except psycopg2.Error:
                return False
    
    def cleanup_test_users(self) -> int:
        """
        Clean up all users created during testing
        
        Returns:
            Number of users cleaned up
        """
        cleanup_count = 0
        users_to_remove = list(self.created_users)  # Create a copy to iterate over
        
        for username in users_to_remove:
            if self.delete_user(username):
                cleanup_count += 1
                print(f"  ✓ Cleaned up test user: {username}")
            else:
                print(f"  ⚠ Failed to clean up test user: {username}")
                
        return cleanup_count
    
    def reset_test_environment(self):
        """Reset the test environment by cleaning up all test users"""
        print("🧹 Resetting test environment...")
        
        # Also clean up any standard test users that might exist
        standard_test_users = [
            'test_admin', 'test_user', 'admin', 'user',
            'integration_admin', 'integration_user'
        ]
        
        with self.database_connection():
            try:
                c = self.conn.cursor()
                for username in standard_test_users:
                    c.execute("DELETE FROM users WHERE username = %s", (username,))
                    if c.rowcount > 0:
                        print(f"  ✓ Removed standard test user: {username}")
            except psycopg2.Error as e:
                print(f"  ⚠ Error during standard user cleanup: {e}")
        
        # Clean up tracked users
        cleanup_count = self.cleanup_test_users()
        print(f"🧹 Test environment reset complete. Cleaned up {cleanup_count} users.")
    
    def setup_integration_test_users(self) -> Dict[str, Dict[str, str]]:
        """
        Set up standard users for integration testing
        
        Returns:
            Dict containing user credentials for different roles
        """
        print("👥 Setting up integration test users...")
        
        users = {}
        
        # Create admin user
        admin_creds = self.ensure_admin_user("integration_admin", "admin_test_pass_123!")
        users['admin'] = admin_creds
        print(f"  ✓ Admin user: {admin_creds['username']}")
        
        # Create regular user
        user_creds = self.ensure_regular_user("integration_user", "user_test_pass_123!")
        users['user'] = user_creds
        print(f"  ✓ Regular user: {user_creds['username']}")
        
        # For backward compatibility, also create 'admin' user if needed
        if not self.user_exists("admin"):
            compat_admin = self.ensure_admin_user("admin", "admin")
            users['compat_admin'] = compat_admin
            print(f"  ✓ Compatibility admin user: {compat_admin['username']}")
        
        return users


def get_test_connection_params() -> Dict[str, Any]:
    """Get database connection parameters for tests"""
    # Check if we're running in Docker (containers use 'postgres' hostname)
    # or locally (use 'localhost')
    import subprocess
    try:
        # Check if we're in a container by looking for docker env or postgres hostname resolution
        result = subprocess.run(['getent', 'hosts', 'postgres'], capture_output=True)
        if result.returncode == 0:
            # We're in a container environment
            host = 'postgres'
        else:
            # We're on localhost
            host = 'localhost'
    except:
        # Default to localhost
        host = 'localhost'
    
    return {
        'host': host,
        'database': os.getenv('POSTGRES_DB', 'budget_test_db'),
        'user': os.getenv('POSTGRES_USER', 'budget_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'budget_password_2025'),
        'port': int(os.getenv('POSTGRES_PORT', '5432'))
    }


@contextmanager 
def test_user_manager(connection_params: Dict[str, Any] = None):
    """
    Context manager for test user management with automatic cleanup
    
    Usage:
        with test_user_manager() as user_mgr:
            admin = user_mgr.ensure_admin_user()
            # ... run tests ...
        # Users are automatically cleaned up here
    """
    if connection_params is None:
        connection_params = get_test_connection_params()
        
    manager = IntegrationTestUserManager(connection_params)
    try:
        manager.connect()
        yield manager
    finally:
        manager.cleanup_test_users()
        manager.close()
