"""Script to list all tables and their details from SQL Server database."""

import pyodbc
import logging
from typing import List, Dict
from tabulate import tabulate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s'
)
logger = logging.getLogger(__name__)

def get_connection():
    """Create database connection."""
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER="
        "DATABASE=;"
        "UID=;"
        "PWD="
    )
    return pyodbc.connect(conn_str)

def get_table_info() -> List[Dict]:
    """Get detailed information about all tables in the database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Query to get table information including row counts and schema
        query = """
        SELECT 
            t.TABLE_SCHEMA as schema_name,
            t.TABLE_NAME as table_name,
            t.TABLE_TYPE as table_type,
            (
                SELECT COUNT(1) 
                FROM INFORMATION_SCHEMA.COLUMNS c 
                WHERE c.TABLE_NAME = t.TABLE_NAME 
                    AND c.TABLE_SCHEMA = t.TABLE_SCHEMA
            ) as column_count,
            CAST(
                CASE 
                    WHEN p.rows IS NULL THEN 0 
                    ELSE p.rows 
                END AS VARCHAR
            ) as row_count
        FROM INFORMATION_SCHEMA.TABLES t
        LEFT JOIN sys.partitions p ON p.object_id = OBJECT_ID(t.TABLE_SCHEMA + '.' + t.TABLE_NAME)
            AND p.index_id IN (0,1)
        WHERE t.TABLE_TYPE = 'BASE TABLE'
        ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME;
        """

        cursor.execute(query)
        tables = []

        for row in cursor.fetchall():
            tables.append({
                'Schema': row.schema_name,
                'Table Name': row.table_name,
                'Type': row.table_type,
                'Columns': row.column_count,
                'Rows': row.row_count
            })

        cursor.close()
        conn.close()

        return tables

    except pyodbc.Error as e:
        logger.error(f"Database error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise

def get_table_columns(table_name: str, schema: str = 'dbo') -> List[Dict]:
    """Get column information for a specific table."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        SELECT 
            c.COLUMN_NAME,
            c.DATA_TYPE,
            c.CHARACTER_MAXIMUM_LENGTH,
            c.IS_NULLABLE,
            CASE 
                WHEN pk.COLUMN_NAME IS NOT NULL THEN 'YES'
                ELSE 'NO'
            END as IS_PRIMARY_KEY
        FROM INFORMATION_SCHEMA.COLUMNS c
        LEFT JOIN (
            SELECT ku.TABLE_CATALOG,ku.TABLE_SCHEMA,ku.TABLE_NAME,ku.COLUMN_NAME
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS AS tc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE AS ku
                ON tc.CONSTRAINT_TYPE = 'PRIMARY KEY' 
                AND tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
        ) pk 
        ON c.TABLE_CATALOG = pk.TABLE_CATALOG 
            AND c.TABLE_SCHEMA = pk.TABLE_SCHEMA
            AND c.TABLE_NAME = pk.TABLE_NAME 
            AND c.COLUMN_NAME = pk.COLUMN_NAME
        WHERE c.TABLE_NAME = ? AND c.TABLE_SCHEMA = ?
        ORDER BY c.ORDINAL_POSITION;
        """

        cursor.execute(query, (table_name, schema))
        columns = []

        for row in cursor.fetchall():
            data_type = row.DATA_TYPE
            if row.CHARACTER_MAXIMUM_LENGTH:
                data_type += f"({row.CHARACTER_MAXIMUM_LENGTH})"

            columns.append({
                'Column': row.COLUMN_NAME,
                'Type': data_type,
                'Nullable': row.IS_NULLABLE,
                'PK': row.IS_PRIMARY_KEY
            })

        cursor.close()
        conn.close()

        return columns

    except pyodbc.Error as e:
        logger.error(f"Database error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise

def main():
    """Main function to list tables and their details."""
    try:
        # Get all tables
        logger.info("Retrieving table information...")
        tables = get_table_info()

        # Print table list
        print("\nDatabase Tables:")
        print(tabulate(tables, headers='keys', tablefmt='grid'))

        # Ask if user wants to see column details for a specific table
        while True:
            table_name = input("\nEnter table name to see columns (or 'q' to quit): ").strip()

            if table_name.lower() == 'q':
                break

            if table_name:
                schema = input("Enter schema name (press Enter for 'dbo'): ").strip() or 'dbo'
                columns = get_table_columns(table_name, schema)

                if columns:
                    print(f"\nColumns for {schema}.{table_name}:")
                    print(tabulate(columns, headers='keys', tablefmt='grid'))
                else:
                    print(f"No columns found for table {schema}.{table_name}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()