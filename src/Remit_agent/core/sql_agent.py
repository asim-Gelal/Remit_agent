"""Enhanced SQL agent module with structured state management."""

from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from sqlalchemy import text

from ..database import get_db
from ..config import settings
from ..logger import get_logger
from ..tools.tools import (
    check_relevance,
    convert_to_sql,
    execute_sql_query,
    generate_human_readable,
)

logger = get_logger(__name__)

class SQLAgent:
    """Enhanced SQL Agent with structured relevance checking."""

    def __init__(self):
        """Initialize the SQL agent with its workflow."""
        logger.info("Initializing SQL Agent...")
        self.workflow = self._create_workflow()

        # Test database connection and log the number of tables
        try:
            with get_db() as db:
                # Test connection
                db.execute(text("SELECT 1"))
                logger.info("Database connection successful")

                # Get the number of tables
                tables_count_query = text("""
                    SELECT COUNT(*) as table_count
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = 'dbo'
                    AND TABLE_TYPE = 'BASE TABLE'
                """)
                tables_count = db.execute(tables_count_query).scalar()
                logger.info(f"Number of tables in the database: {tables_count}")

        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise RuntimeError(f"Database connection failed: {str(e)}")

        logger.info("SQL Agent initialized successfully")

    def _check_relevance(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Check question relevance and analyze components."""
        try:
            logger.info(f"Checking relevance for question: {state['question']}")
            relevance_result = check_relevance(state["question"])
            logger.info(f"Relevance check result: {relevance_result}")
            return {**state, "relevance_result": relevance_result}

        except Exception as e:
            error_msg = f"Error in relevance check: {str(e)}"
            logger.error(error_msg)
            return {
                **state,
                "relevance_result": {
                    "relevant": False,
                    "explanation": error_msg,
                    "tables": [],
                    "breakdown": {
                        "intent": "unknown",
                        "entities": [],
                        "conditions": [],
                        "timeframe": "none"
                    }
                }
            }

    def _convert_to_sql(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Convert natural language to SQL using relevance analysis."""
        try:
            sql_query = convert_to_sql(
                state["question"],
                state["relevance_result"]
            )

            logger.info(f"Generated SQL query: {sql_query}")
            return {
                **state,
                "sql_query": sql_query if sql_query else "",
                "sql_error": not bool(sql_query)
            }
        except Exception as e:
            error_msg = f"Error in SQL conversion: {str(e)}"
            logger.error(error_msg)
            return {
                **state,
                "sql_error": True,
                "sql_query": "",
                "query_result": error_msg
            }

    def _execute_sql(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SQL query with enhanced error handling."""
        if not state["sql_query"]:
            logger.warning("No SQL query to execute")
            return {
                **state,
                "sql_error": True,
                "query_result": "Failed to generate SQL query"
            }

        try:
            result = execute_sql_query(state["sql_query"])

            if not result.get("success"):
                error_msg = result.get("error", "Unknown error during query execution")
                logger.error(f"SQL execution error: {error_msg}")
                return {
                    **state,
                    "sql_error": True,
                    "query_result": f"Error: {error_msg}"
                }

            logger.info("SQL query executed successfully")
            return {
                **state,
                "sql_error": False,
                "query_rows": result.get("rows", []),
                "columns": result.get("columns", []),
                "query_result": "Query executed successfully"
            }
        except Exception as e:
            error_msg = f"Error executing SQL: {str(e)}"
            logger.error(error_msg)
            return {
                **state,
                "sql_error": True,
                "query_result": error_msg
            }

    def _generate_human_readable(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate human-readable response with context awareness."""
        try:
            response = generate_human_readable(
                state["sql_query"],
                {
                    "rows": state["query_rows"],
                    "columns": state["columns"],
                    "success": not state["sql_error"],
                    "question": state["question"]
                }
            )

            logger.info("Human readable response generated successfully")
            return {**state, "query_result": response}

        except Exception as e:
            error_msg = f"Error generating readable response: {str(e)}"
            logger.error(error_msg)
            return {**state, "query_result": error_msg}

    def _create_workflow(self) -> StateGraph:
        """Create the workflow graph."""
        workflow = StateGraph(Dict)  # Use Dict as the state type

        # Define nodes
        workflow.add_node("check_relevance", self._check_relevance)
        workflow.add_node("convert_to_sql", self._convert_to_sql)
        workflow.add_node("execute_sql", self._execute_sql)
        workflow.add_node("generate_human_readable", self._generate_human_readable)

        # Set entry point
        workflow.set_entry_point("check_relevance")

        # Add edges
        workflow.add_conditional_edges(
            "check_relevance",
            lambda x: "convert_to_sql" if x["relevance_result"].get("relevant", False) else END,
            {
                "convert_to_sql": "convert_to_sql",
                END: END
            }
        )

        workflow.add_edge("convert_to_sql", "execute_sql")
        workflow.add_edge("execute_sql", "generate_human_readable")
        workflow.add_edge("generate_human_readable", END)

        return workflow.compile()

    def run(self, question: str) -> Dict[str, Any]:
        """Run the SQL agent workflow."""
        try:
            logger.info(f"Starting workflow with question: {question}")
            initial_state = {
                "question": question,
                "relevance_result": None,
                "sql_query": "",
                "query_result": "",
                "query_rows": [],
                "columns": [],
                "attempts": 0,
                "sql_error": False
            }

            result = self.workflow.invoke(initial_state)

            if isinstance(result, dict):
                return {
                    "query_result": result.get("query_result", "Error processing request"),
                    "relevance_result": result.get("relevance_result"),
                    "sql_query": result.get("sql_query")
                }
            else:
                logger.error(f"Unexpected result type: {type(result)}")
                return {
                    "query_result": "Error: Unexpected result type",
                    "relevance_result": None,
                    "sql_query": None
                }

        except Exception as e:
            logger.error(f"Error running workflow: {str(e)}")
            return {
                "query_result": f"Error processing request: {str(e)}",
                "relevance_result": None,
                "sql_query": None
            }