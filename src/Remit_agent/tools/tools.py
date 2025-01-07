"""Enhanced tools for the SQL Agent with simplified implementation."""

import json
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from sqlalchemy import text

from ..config import settings
from ..database import get_db, get_database_schema
from ..logger import get_logger
from ..prompts import (
    RELEVANCE_CHECK_PROMPT,
    SQL_CONVERSION_PROMPT,
    HUMAN_READABLE_PROMPT,
)
from .tool_monitoring import tool_monitor

logger = get_logger(__name__)

# Initialize LLM
llm = ChatOpenAI(temperature=settings.TEMPERATURE, model=settings.MODEL_NAME)

@tool_monitor
def check_relevance(question: str) -> Dict[str, Any]:
    """Check if a question is relevant to the database schema and analyze its components."""
    logger.info(f"Checking relevance for question: {question}")

    try:
        # Get response from LLM
        chain = RELEVANCE_CHECK_PROMPT | llm | StrOutputParser()
        result = chain.invoke({"question": question})

        # Log the raw response for debugging
        logger.debug(f"Raw LLM response: {result}")

        # Parse JSON response
        try:
            parsed_result = json.loads(result)

            # Provide default values if missing
            default_response = {
                "relevant": False,
                "tables": [],
                "breakdown": {
                    "intent": "unknown",
                    "entities": [],
                    "conditions": [],
                    "timeframe": "none"
                },
                "explanation": "No explanation provided"
            }

            if isinstance(parsed_result, dict):
                # Merge with defaults
                default_response.update(parsed_result)
                logger.info(f"Relevance check completed: {default_response}")
                return default_response
            else:
                logger.error("Response is not a dictionary")
                return default_response

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse relevance check response: {e}")
            logger.error(f"Raw response that failed to parse: {result}")
            return {
                "relevant": False,
                "tables": [],
                "breakdown": {
                    "intent": "unknown",
                    "entities": [],
                    "conditions": [],
                    "timeframe": "none"
                },
                "explanation": "Failed to parse response"
            }

    except Exception as e:
        logger.error(f"Error in relevance check: {str(e)}")
        return {
            "relevant": False,
            "tables": [],
            "breakdown": {
                "intent": "unknown",
                "entities": [],
                "conditions": [],
                "timeframe": "none"
            },
            "explanation": f"Error: {str(e)}"
        }

@tool_monitor
def convert_to_sql(question: str, context: Dict[str, Any]) -> Optional[str]:
    """Convert natural language to SQL query using relevance analysis."""
    logger.info(f"Converting to SQL - Question: {question}")
    logger.info(f"Context: {context}")

    try:
        # Get schemas for relevant tables
        schema = get_database_schema()

        # Prepare the input for SQL conversion
        chain = SQL_CONVERSION_PROMPT | llm | StrOutputParser()
        result = chain.invoke({
            "schema": schema,
            "question": question,
            "breakdown": context  # Pass the entire context as {breakdown}
        })

        logger.info(f"Generated SQL query: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in SQL conversion: {str(e)}")
        return None

@tool_monitor
def execute_sql_query(query: str) -> Dict[str, Any]:
    """Execute SQL query and return the results."""
    logger.info(f"Executing SQL query: {query}")

    with get_db() as db:
        try:
            # Execute query
            result = db.execute(text(query))

            if query.lower().strip().startswith("select"):
                rows = result.fetchall()
                columns = list(result.keys())

                # Convert rows to list of dicts
                formatted_rows = [dict(zip(columns, row)) for row in rows]

                return {
                    "success": True,
                    "rows": formatted_rows,
                    "columns": columns
                }
            else:
                db.commit()
                return {"success": True}

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error executing query: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }

@tool_monitor
def generate_human_readable(sql: str, result: Dict[str, Any]) -> str:
    """Generate a human-readable response from SQL query results."""
    logger.info("Generating human readable response")
    logger.info(f"Input SQL: {sql}")

    try:
        chain = HUMAN_READABLE_PROMPT | llm | StrOutputParser()
        response = chain.invoke({
            "sql": sql,
            "result": result
        })

        logger.info(f"Generated response: {response}")
        return response

    except Exception as e:
        logger.error(f"Error generating readable response: {str(e)}")
        return f"Error processing results: {str(e)}"