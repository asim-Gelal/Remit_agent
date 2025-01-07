"""Logging configuration module for centralized logging management.

This module provides a centralized logging configuration that creates a single log file
per program execution, with the filename containing project name and timestamp.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from Remit_agent.config import settings  # Updated import path

class SingletonLogger:
    """Singleton class to manage logging configuration and ensure single file per run."""

    _instance: Optional['SingletonLogger'] = None
    _log_file: Optional[Path] = None
    _initialized: bool = False

    def __new__(cls) -> 'SingletonLogger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not self._initialized:
            self._initialized = True
            self._setup_log_directory()
            self._create_log_file()

    def _setup_log_directory(self) -> None:
        """Ensure log directory exists."""
        settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    def _create_log_file(self) -> None:
        """Create a new log file with timestamp if it doesn't exist."""
        if self._log_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._log_file = settings.LOGS_DIR / f"{settings.PROJECT_NAME}_{timestamp}.log"

    def get_log_file(self) -> Path:
        """Return the current log file path."""
        return self._log_file

def get_logger(name: str) -> logging.Logger:
    """Configure and return a logger instance that writes to the centralized log file.

    Args:
        name: The name of the logger, typically __name__ from the calling module.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)

    # Return existing logger if already configured
    if logger.handlers:
        return logger

    logger.setLevel(settings.LOG_LEVEL)
    formatter = logging.Formatter(settings.LOG_FORMAT)

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Add file handler using singleton log file
    log_manager = SingletonLogger()
    file_handler = logging.FileHandler(log_manager.get_log_file())
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Log initialization message
    logger.info(f"Logger initialized: {name}")
    return logger

def get_current_log_file() -> Path:
    """Return the path of the current log file.

    Returns:
        Path: Path object pointing to the current log file.
    """
    return SingletonLogger().get_log_file()