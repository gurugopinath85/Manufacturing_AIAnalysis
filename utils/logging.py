"""
Logging configuration and utilities.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.config import get_settings


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color coding for different log levels."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up application logging.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to a file
        log_file: Custom log file path (optional)
        
    Returns:
        Configured logger instance
    """
    settings = get_settings()
    
    # Create logger
    logger = logging.getLogger("manufacturing_ai")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO if not settings.debug else logging.DEBUG)
    
    # Format for console (with colors in debug mode)
    if settings.debug:
        console_format = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_format = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler
    if log_to_file:
        if log_file is None:
            # Create logs directory
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            log_file = logs_dir / f"manufacturing_ai_{datetime.now().strftime('%Y%m%d')}.log"
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    # Prevent duplicate logs
    logger.propagate = False
    
    return logger


def get_logger(name: str = "manufacturing_ai") -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


class LoggingContext:
    """Context manager for temporary logging configuration."""
    
    def __init__(self, logger: logging.Logger, level: str):
        self.logger = logger
        self.new_level = getattr(logging, level.upper())
        self.old_level = None
    
    def __enter__(self):
        self.old_level = self.logger.level
        self.logger.setLevel(self.new_level)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.old_level)


def log_execution_time(func):
    """Decorator to log function execution time."""
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger()
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.2f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f} seconds: {str(e)}")
            raise
    
    return wrapper


def log_dataframe_info(df, name: str = "DataFrame"):
    """Log information about a pandas DataFrame."""
    logger = get_logger()
    logger.info(f"{name} shape: {df.shape}")
    logger.info(f"{name} columns: {list(df.columns)}")
    logger.debug(f"{name} dtypes:\n{df.dtypes}")
    
    # Log memory usage if significant
    memory_usage = df.memory_usage(deep=True).sum() / 1024 / 1024  # MB
    if memory_usage > 10:
        logger.info(f"{name} memory usage: {memory_usage:.1f} MB")


def log_api_request(endpoint: str, method: str, params: dict = None):
    """Log API request details."""
    logger = get_logger()
    logger.info(f"API Request: {method} {endpoint}")
    if params:
        logger.debug(f"Parameters: {params}")


def log_llm_usage(provider: str, tokens_used: int, cost_estimate: float = None):
    """Log LLM API usage."""
    logger = get_logger()
    logger.info(f"LLM Usage - Provider: {provider}, Tokens: {tokens_used}")
    if cost_estimate:
        logger.info(f"Estimated cost: ${cost_estimate:.4f}")


# Initialize default logger
_default_logger = None


def init_logging():
    """Initialize the default logger for the application."""
    global _default_logger
    settings = get_settings()
    level = "DEBUG" if settings.debug else "INFO"
    _default_logger = setup_logging(level=level)
    return _default_logger


def get_default_logger():
    """Get the default application logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = init_logging()
    return _default_logger
