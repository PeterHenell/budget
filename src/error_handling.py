"""
Centralized Error Handling Framework

Provides standardized error handling patterns for database operations,
web responses, and user messaging across the budget application.

Following DEVELOPMENT_GUIDELINES.md:
- Fail fast principle
- Structured logging  
- Consistent user experience
- Proper exception handling
"""

from typing import Dict, Any, Optional, Tuple, Callable
from functools import wraps
from flask import flash, jsonify, request
import psycopg2
from logging_config import get_logger

logger = get_logger(__name__)


class BudgetError(Exception):
    """Base exception class for budget application errors"""
    
    def __init__(self, message: str, error_code: str = "GENERAL_ERROR", 
                 details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(BudgetError):
    """Database-related errors"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.original_error = original_error
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details={"original_error": str(original_error) if original_error else None}
        )


class ValidationError(BudgetError):
    """Input validation errors"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR", 
            details={"field": field}
        )


class AuthenticationError(BudgetError):
    """Authentication and authorization errors"""
    
    def __init__(self, message: str):
        super().__init__(
            message=message,
            error_code="AUTH_ERROR"
        )


class ClassificationError(BudgetError):
    """Transaction classification errors"""
    
    def __init__(self, message: str, transaction_id: Optional[int] = None):
        super().__init__(
            message=message,
            error_code="CLASSIFICATION_ERROR",
            details={"transaction_id": transaction_id}
        )


def handle_database_connection(func: Callable) -> Callable:
    """
    Decorator to handle database connection errors consistently.
    
    Usage:
        @handle_database_connection
        def my_route():
            logic = get_logic()
            # database operations...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f'Database connection failed in {func.__name__}: {e}')
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Database connection failed',
                    'error_code': 'DATABASE_CONNECTION_ERROR'
                }), 500
            else:
                flash('Database connection failed', 'error')
                return redirect(url_for('dashboard'))
    
    return wrapper


def standardize_flash_message(message: str, category: str, 
                            log_level: str = 'info') -> None:
    """
    Standardized flash message with consistent logging.
    
    Args:
        message: User-facing message
        category: Flask flash category ('success', 'info', 'warning', 'error')  
        log_level: Logging level ('debug', 'info', 'warning', 'error', 'critical')
    """
    # Log the message
    log_func = getattr(logger, log_level.lower(), logger.info)
    log_func(f"Flash message [{category}]: {message}")
    
    # Flash to user
    flash(message, category)


def create_error_response(error: BudgetError, is_json: bool = None) -> Tuple[Any, int]:
    """
    Create standardized error response for web or API requests.
    
    Args:
        error: BudgetError instance
        is_json: Force JSON response format (auto-detected if None)
        
    Returns:
        Tuple of (response, status_code)
    """
    if is_json is None:
        is_json = request.is_json if request else False
    
    # Log the error
    logger.error(f"Error [{error.error_code}]: {error.message}", 
                extra={"error_details": error.details})
    
    if is_json:
        return jsonify({
            'success': False,
            'error': error.message,
            'error_code': error.error_code,
            'details': error.details
        }), _get_status_code(error.error_code)
    else:
        # Web interface - flash message and return redirect
        category = _get_flash_category(error.error_code)
        standardize_flash_message(error.message, category, 'error')
        return None, _get_status_code(error.error_code)


def handle_database_operation(operation_name: str):
    """
    Decorator for database operations with standardized error handling.
    
    Usage:
        @handle_database_operation("create_category")
        def create_category(self, name: str):
            # database operations...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except psycopg2.IntegrityError as e:
                raise ValidationError(f"Data integrity violation in {operation_name}: {str(e)}")
            except psycopg2.Error as e:
                raise DatabaseError(f"Database error in {operation_name}: {str(e)}", e)
            except Exception as e:
                logger.error(f"Unexpected error in {operation_name}: {e}")
                raise BudgetError(f"Unexpected error in {operation_name}: {str(e)}")
        
        return wrapper
    return decorator


def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None:
    """
    Validate that required fields are present and not empty.
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        
    Raises:
        ValidationError: If any required field is missing or empty
    """
    missing_fields = []
    empty_fields = []
    
    for field in required_fields:
        if field not in data:
            missing_fields.append(field)
        elif not data[field] or (isinstance(data[field], str) and not data[field].strip()):
            empty_fields.append(field)
    
    if missing_fields:
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
    
    if empty_fields:
        raise ValidationError(f"Empty required fields: {', '.join(empty_fields)}")


def _get_status_code(error_code: str) -> int:
    """Map error codes to HTTP status codes"""
    status_map = {
        'VALIDATION_ERROR': 400,
        'AUTH_ERROR': 401, 
        'DATABASE_ERROR': 500,
        'CLASSIFICATION_ERROR': 500,
        'GENERAL_ERROR': 500
    }
    return status_map.get(error_code, 500)


def _get_flash_category(error_code: str) -> str:
    """Map error codes to flash message categories"""
    category_map = {
        'VALIDATION_ERROR': 'warning',
        'AUTH_ERROR': 'error',
        'DATABASE_ERROR': 'error', 
        'CLASSIFICATION_ERROR': 'warning',
        'GENERAL_ERROR': 'error'
    }
    return category_map.get(error_code, 'error')


# Context manager for database transactions
class DatabaseTransaction:
    """Context manager for database transactions with proper error handling"""
    
    def __init__(self, connection):
        self.connection = connection
        self.cursor = None
        
    def __enter__(self):
        self.cursor = self.connection.cursor()
        return self.cursor
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Success - commit the transaction
            self.connection.commit()
        else:
            # Error occurred - rollback
            self.connection.rollback()
            logger.error(f"Database transaction rolled back: {exc_val}")
            
        if self.cursor:
            self.cursor.close()
            
        return False  # Re-raise any exceptions
