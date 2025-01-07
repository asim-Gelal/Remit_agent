"""Test script for database connection and schema retrieval."""

import sys
import os
from pathlib import Path
from sqlalchemy import text

# Add the project root to Python path
project_root = Path(__file__).parent.parent / "src"
sys.path.append(str(project_root))

from Remit_agent.config import settings
from Remit_agent.database import get_db, get_database_schema, engine, INCLUDED_TABLES
from Remit_agent.logger import get_logger

logger = get_logger(__name__)

def test_basic_connection():
    """Test basic database connectivity."""
    logger.info("Testing basic database connection...")

    try:
        # Test connection using engine
        with engine.connect() as connection:
            # Use text() for raw SQL
            version_query = text("SELECT @@VERSION")
            version = connection.execute(version_query).scalar()
            logger.info("✅ Database connection successful")
            logger.info(f"SQL Server Version: {version[:100]}...")  # Show first 100 chars
            return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False

def test_session_management():
    """Test database session creation and management."""
    logger.info("Testing database session management...")

    try:
        with get_db() as db:
            # Use text() for raw SQL
            query = text("SELECT DB_NAME() as database_name")
            result = db.execute(query).scalar()
            logger.info(f"✅ Successfully connected to database: {result}")
            return True
    except Exception as e:
        logger.error(f"❌ Session management test failed: {str(e)}")
        return False

def test_table_access():
    """Test access to whitelisted tables."""
    logger.info("Testing access to whitelisted tables...")

    try:
        with get_db() as db:
            for table_name in INCLUDED_TABLES:
                schema, table = table_name.split('.')
                # Use text() for raw SQL and proper parameter binding
                query = text(f"SELECT COUNT(*) FROM {schema}.{table}")
                count = db.execute(query).scalar()
                logger.info(f"✅ Successfully accessed {table_name} - Row count: {count}")
            return True
    except Exception as e:
        logger.error(f"❌ Table access test failed: {str(e)}")
        return False

def test_table_schema():
    """Test direct schema retrieval for specific tables."""
    logger.info("Testing direct table schema retrieval...")

    try:
        with get_db() as db:
            for table_name in INCLUDED_TABLES:
                schema, table = table_name.split('.')
                # Query column information directly using INFORMATION_SCHEMA
                query = text("""
                    SELECT 
                        c.COLUMN_NAME,
                        c.DATA_TYPE,
                        c.CHARACTER_MAXIMUM_LENGTH,
                        c.IS_NULLABLE
                    FROM INFORMATION_SCHEMA.COLUMNS c
                    WHERE c.TABLE_SCHEMA = :schema
                    AND c.TABLE_NAME = :table
                    ORDER BY c.ORDINAL_POSITION
                """)

                results = db.execute(query, {"schema": schema, "table": table})
                columns = results.fetchall()

                logger.info(f"\nTable: {table_name}")
                for col in columns:
                    logger.info(f"Column: {col.COLUMN_NAME}, Type: {col.DATA_TYPE}, "
                              f"Length: {col.CHARACTER_MAXIMUM_LENGTH}, "
                              f"Nullable: {col.IS_NULLABLE}")
            return True
    except Exception as e:
        logger.error(f"❌ Table schema test failed: {str(e)}")
        return False

def main():
    """Run all database connection tests."""
    logger.info("=== Starting Database Connection Tests ===")
    logger.info(f"Database Server: {settings.DB_SERVER}")
    logger.info(f"Database Name: {settings.DB_NAME}")
    logger.info(f"Whitelisted Tables: {', '.join(INCLUDED_TABLES)}")

    # Run all tests
    tests = [
        ("Basic Connection", test_basic_connection),
        ("Session Management", test_session_management),
        ("Table Access", test_table_access),
        ("Table Schema", test_table_schema)
    ]

    success = True
    for test_name, test_func in tests:
        logger.info(f"\n=== Running Test: {test_name} ===")
        if not test_func():
            success = False
            logger.error(f"❌ {test_name} test failed")
        else:
            logger.info(f"✅ {test_name} test passed")

    # Final status
    if success:
        logger.info("\n=== All tests passed successfully! ===")
    else:
        logger.error("\n=== Some tests failed! Please check the logs for details ===")

if __name__ == "__main__":
    main()