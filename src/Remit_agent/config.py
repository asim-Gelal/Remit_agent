"""Configuration module for the application.

This module handles environment variables and configuration settings.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Project settings and configurations."""

    def __init__(self):
        """Initialize settings from environment variables."""
        # Project Configuration
        self.PROJECT_NAME = os.getenv("PROJECT_NAME", "remit_agent")
        self.BASE_DIR = Path(__file__).parent
        self.LOGS_DIR = self.BASE_DIR / "logs"
        self.LOG_LEVEL = int(os.getenv("LOG_LEVEL", logging.INFO))
        self.LOG_FORMAT = os.getenv(
            "LOG_FORMAT",
            "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        )

        # OpenAI Configuration
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")
        self.TEMPERATURE = float(os.getenv("TEMPERATURE", 0.0))

        # LangChain Configuration
        self.LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
        if not self.LANGCHAIN_API_KEY:
            raise ValueError("LANGCHAIN_API_KEY environment variable is required")
        self.LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        self.LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "sqlAgent")

        # Tavily Configuration
        self.TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
        if not self.TAVILY_API_KEY:
            raise ValueError("TAVILY_API_KEY environment variable is required")

        # Database Configuration
        self.DB_TYPE = os.getenv("DB_TYPE")
        if not self.DB_TYPE:
            raise ValueError("DB_TYPE environment variable is required")
        self.DB_DRIVER = os.getenv("DB_DRIVER")
        if not self.DB_DRIVER:
            raise ValueError("DB_DRIVER environment variable is required")
        self.DB_SERVER = os.getenv("DB_SERVER")
        if not self.DB_SERVER:
            raise ValueError("DB_SERVER environment variable is required")
        self.DB_NAME = os.getenv("DB_NAME")
        if not self.DB_NAME:
            raise ValueError("DB_NAME environment variable is required")
        self.DB_USER = os.getenv("DB_USER")
        if not self.DB_USER:
            raise ValueError("DB_USER environment variable is required")
        self.DB_PASSWORD = os.getenv("DB_PASSWORD")
        if not self.DB_PASSWORD:
            raise ValueError("DB_PASSWORD environment variable is required")
        self.DB_PORT = int(os.getenv("DB_PORT"))
        if not self.DB_PORT:
            raise ValueError("DB_PORT environment variable is required")

        # Tool Configuration
        self.MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
        self.BATCH_SIZE = int(os.getenv("BATCH_SIZE", 1000))

        # Error Handling Configuration
        self.MAX_ERROR_LENGTH = int(os.getenv("MAX_ERROR_LENGTH", 1000))
        self.RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", 1))

        # Create logs directory if it doesn't exist
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def connection_string(self) -> str:
        """Generate database connection string."""
        # Strip any comments or whitespace from DB_TYPE
        db_type = self.DB_TYPE.lower().strip().split("#")[0].strip()

        if db_type == "mssql":
            # Ensure driver name is properly formatted
            driver = self.DB_DRIVER.replace(" ", "+")
            return (
                f"mssql+pyodbc://{self.DB_USER}:{self.DB_PASSWORD}@"
                f"{self.DB_SERVER}:{self.DB_PORT}/{self.DB_NAME}"
                f"?driver={driver}"
            )
        raise ValueError(
            f"Unsupported database type: {db_type}. "
            "Currently only 'mssql' is supported."
        )

# Create a global instance for settings
settings = Settings()