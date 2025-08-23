"""
Logging Configuration for Budget Application
Provides centralized logging setup with proper levels, formatting, and handlers
"""

import logging
import logging.handlers
import os
import sys
from typing import Optional


def setup_logging(
    level: str = "INFO", 
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up centralized logging for the budget application
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path. If None, logs only to console
        max_bytes: Maximum size for log file rotation
        backup_count: Number of backup log files to keep
        
    Returns:
        Configured logger instance
    """
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter with detailed information
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Get or create logger
    logger = logging.getLogger('budget_app')
    logger.setLevel(numeric_level)
    
    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler (always present)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            sys.stderr.write(f"Log directory does not exist: {log_dir}\n")
            sys.exit(1)

        # Rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=max_bytes, 
            backupCount=backup_count
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str = 'budget_app') -> logging.Logger:
    """
    Get a logger instance for a specific module
    
    Args:
        name: Logger name (usually module name)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Initialize default logger configuration
def init_logging():
    """Initialize logging with environment-based configuration"""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_file = os.getenv('LOG_FILE')  # Optional
    environment = os.getenv('ENVIRONMENT', 'production')
    
    # Environment-specific defaults
    if environment.lower() == 'development':
        log_level = os.getenv('LOG_LEVEL', 'DEBUG')
        # Enable more verbose console output for development
        return setup_logging(level=log_level, log_file=log_file)
    
    elif environment.lower() == 'test':
        log_level = os.getenv('LOG_LEVEL', 'WARNING')
        # Minimize logging during tests
        return setup_logging(level=log_level, log_file=log_file)
    
    else:
        # Production: Log to file and console with INFO level
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        if not log_file:
            log_file = '/app/logs/budget.log'  # Default production log file
        return setup_logging(level=log_level, log_file=log_file)


# Default logger instance
logger = get_logger()
