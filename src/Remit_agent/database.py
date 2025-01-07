"""Database connection and schema management module."""

from sqlalchemy import create_engine, inspect, event,text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine import Engine
from contextlib import contextmanager
from typing import Generator, List, Set
import pyodbc

from .config import settings
from .logger import get_logger

logger = get_logger(__name__)

# Define tables to include in schema
INCLUDED_TABLES: Set[str] = {
    'dbo.remitTransactions',
    'dbo.customers'
}

def create_db_engine() -> Engine:
    """Create and configure the database engine with proper MSSQL settings."""
    try:
        # Using simplified connection string from settings
        engine = create_engine(
            settings.connection_string,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
        )

        @event.listens_for(engine, 'connect')
        def receive_connect(dbapi_connection, connection_record):
            logger.info("New database connection established")

        return engine

    except Exception as e:
        logger.error(f"Failed to create database engine: {str(e)}")
        raise

# Create database engine
engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Get database session with automatic closing and error handling."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        db.close()

def add_table_to_schema(table_name: str) -> bool:
    """Add a new table to the schema whitelist."""
    if table_name in INCLUDED_TABLES:
        logger.info(f"Table {table_name} already in schema whitelist")
        return False

    INCLUDED_TABLES.add(table_name)
    logger.info(f"Added table {table_name} to schema whitelist")
    return True

def remove_table_from_schema(table_name: str) -> bool:
    """Remove a table from the schema whitelist."""
    if table_name not in INCLUDED_TABLES:
        logger.info(f"Table {table_name} not in schema whitelist")
        return False

    INCLUDED_TABLES.remove(table_name)
    logger.info(f"Removed table {table_name} from schema whitelist")
    return True

# def get_database_schema() -> str:
#     """Get database schema as a formatted string for whitelisted tables only."""
#     inspector = inspect(engine)
#     schema_parts = []
#
#     try:
#         # Get all available tables
#         all_tables = set(inspector.get_table_names())
#
#         for table_name in INCLUDED_TABLES:
#             # Split schema and table name
#             schema, table = table_name.split('.') if '.' in table_name else (None, table_name)
#
#             # Verify table exists
#             if table not in all_tables:
#                 logger.warning(f"Table {table_name} not found in database")
#                 continue
#
#             schema_parts.append(f"\nTable: {table_name}")
#
#             try:
#                 columns = inspector.get_columns(table, schema=schema)
#                 pk_constraint = inspector.get_pk_constraint(table, schema=schema)
#                 pk_columns = set(pk_constraint['constrained_columns']) if pk_constraint else set()
#                 fk_info = inspector.get_foreign_keys(table, schema=schema)
#                 fk_dict = {fk['constrained_columns'][0]: fk for fk in fk_info}
#
#                 for column in columns:
#                     col_info = [
#                         f"- {column['name']}: {str(column['type'])}"
#                     ]
#
#                     if column['name'] in pk_columns:
#                         col_info.append("Primary Key")
#
#                     if column['name'] in fk_dict:
#                         fk = fk_dict[column['name']]
#                         col_info.append(
#                             f"Foreign Key to {fk['referred_table']}.{fk['referred_columns'][0]}"
#                         )
#
#                     schema_parts.append(", ".join(col_info))
#             except Exception as e:
#                 logger.error(f"Error getting schema for table {table_name}: {str(e)}")
#                 schema_parts.append(f"Error retrieving columns: {str(e)}")
#
#             schema_parts.append("")  # Empty line between tables
#
#         schema_str = "\n".join(schema_parts)
#         logger.info(f"Retrieved schema for {len(INCLUDED_TABLES)} whitelisted tables")
#         return schema_str
#
#     except Exception as e:
#         error_msg = f"Error retrieving database schema: {str(e)}"
#         logger.error(error_msg)
#         return f"Error: {error_msg}"

def get_database_schema() -> str:
    """Get database schema as a formatted string for specified tables."""
    try:
        with get_db() as db:
            schema_parts = []

            # Query for table schemas
            schema_query = text("""
                SELECT 
                    c.TABLE_NAME,
                    c.COLUMN_NAME,
                    c.DATA_TYPE,
                    c.IS_NULLABLE,
                    CASE 
                        WHEN pk.COLUMN_NAME IS NOT NULL THEN 'YES' 
                        ELSE 'NO' 
                    END as IS_PRIMARY_KEY
                FROM INFORMATION_SCHEMA.COLUMNS c
                LEFT JOIN (
                    SELECT ku.TABLE_NAME, ku.COLUMN_NAME
                    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                    JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
                        ON tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                        AND tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
                ) pk 
                    ON c.TABLE_NAME = pk.TABLE_NAME 
                    AND c.COLUMN_NAME = pk.COLUMN_NAME
                WHERE c.TABLE_SCHEMA = 'dbo'
                AND c.TABLE_NAME IN ('remitTransactions', 'customers')
                ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION
            """)

            current_table = None
            for row in db.execute(schema_query):
                if current_table != row.TABLE_NAME:
                    current_table = row.TABLE_NAME
                    schema_parts.append(f"\nTable: {row.TABLE_NAME}")

                pk_indicator = " (Primary Key)" if row.IS_PRIMARY_KEY == 'YES' else ""
                nullable = "NULL" if row.IS_NULLABLE == 'YES' else "NOT NULL"
                schema_parts.append(
                    f"- {row.COLUMN_NAME}: {row.DATA_TYPE} {nullable}{pk_indicator}"
                )

            schema_str = "\n".join(schema_parts)
            logger.info(f"Retrieved schema:\n{schema_str}")
            return schema_str

    except Exception as e:
        error_msg = f"Error retrieving database schema: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"