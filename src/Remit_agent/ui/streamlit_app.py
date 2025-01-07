"""Streamlit interface for the SQL Agent with tool monitoring."""

import streamlit as st
from typing import Dict, Any
import pandas as pd
import json
from decimal import Decimal
from datetime import datetime, date, time

from Remit_agent.core.sql_agent import SQLAgent
from Remit_agent.logger import get_logger
from Remit_agent.tools.tool_monitoring import tool_monitor

logger = get_logger(__name__)

def initialize_session_state():
    """Initialize session state variables."""
    if 'agent' not in st.session_state:
        st.session_state.agent = SQLAgent()
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'show_monitoring' not in st.session_state:
        st.session_state.show_monitoring = False

def format_query_result(result: Dict[str, Any]) -> str:
    """Format query results for display."""
    if not result or 'query_result' not in result:
        return "No results to display"

    # If the result contains a markdown table, display it properly
    if '|' in result['query_result'] and '-|-' in result['query_result']:
        return result['query_result']

    return result['query_result']

def format_value(value: Any) -> str:
    """Format a value for display in the monitoring panel."""
    class CustomJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.strftime('%Y-%m-%d %H:%M:%S')
            if isinstance(obj, date):
                return obj.strftime('%Y-%m-%d')
            if isinstance(obj, Decimal):
                return str(obj)
            return super().default(obj)

    try:
        if isinstance(value, (dict, list)):
            return json.dumps(value, indent=2, cls=CustomJSONEncoder)
        if isinstance(value, (datetime, date)):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(value, Decimal):
            return str(value)
        return str(value)
    except Exception as e:
        logger.error(f"Error serializing value: {str(e)}")
        return f"Error serializing value: {str(e)}"

def render_monitoring_panel():
    """Render the tool monitoring panel."""
    st.sidebar.title("🔍 Tool Monitoring")

    # Toggle for monitoring panel
    show_monitoring = st.sidebar.toggle(
        "Show Tool Monitoring",
        value=st.session_state.show_monitoring
    )

    if show_monitoring != st.session_state.show_monitoring:
        st.session_state.show_monitoring = show_monitoring
        st.rerun()  # Updated from experimental_rerun to rerun

    if show_monitoring:
        # Clear monitoring button
        if st.sidebar.button("Clear Monitoring Data"):
            tool_monitor.clear()
            st.rerun()  # Updated here as well

        # Display invocations
        invocations = tool_monitor.get_invocations()

        if not invocations:
            st.sidebar.info("No tool invocations recorded yet.")
            return

        for idx, invocation in enumerate(reversed(invocations)):
            with st.sidebar.expander(
                    f"🛠️ {invocation.tool_name} ({invocation.duration:.2f}s)",
                    expanded=(idx == 0)  # Expand only the latest invocation
            ):
                st.markdown("**Timestamp:**")
                st.text(invocation.timestamp.strftime("%Y-%m-%d %H:%M:%S"))

                st.markdown("**Inputs:**")
                st.code(format_value(invocation.inputs))

                st.markdown("**Outputs:**")
                st.code(format_value(invocation.outputs))

def apply_dark_theme():
    """Apply dark theme styling to the Streamlit app."""
    st.markdown("""
        <style>
        /* Dark theme customization */
        .stApp {
            background-color: #0E1117;
        }

        /* Sidebar customization */
        .css-1d391kg {
            background-color: #1E1E1E;
        }

        /* Input box customization */
        .stTextInput > div > div > input {
            background-color: #2D2D2D;
            color: #FFFFFF;
        }

        /* Button customization */
        .stButton > button {
            background-color: #00A6FF;
            color: #FFFFFF;
            border: none;
        }

        /* Chat message customization */
        .user-message {
            background-color: #1E1E1E;
            padding: 1rem;
            border-radius: 5px;
            margin-bottom: 1rem;
        }

        .assistant-message {
            background-color: #2D2D2D;
            padding: 1rem;
            border-radius: 5px;
            margin-bottom: 1rem;
        }

        /* Tool monitoring customization */
        .tool-invocation {
            background-color: #1E1E1E;
            padding: 1rem;
            border-radius: 5px;
            margin-bottom: 0.5rem;
        }

        .tool-details {
            background-color: #2D2D2D;
            padding: 0.5rem;
            border-radius: 3px;
            margin-top: 0.5rem;
        }

        /* Code block customization */
        pre {
            background-color: #1E1E1E !important;
        }

        code {
            color: #00FF9D !important;
        }

        /* Expander customization */
        .streamlit-expanderHeader {
            background-color: #2D2D2D;
            color: #FFFFFF;
        }

        /* Table customization */
        .stTable {
            background-color: #1E1E1E;
        }

        th {
            background-color: #2D2D2D;
            color: #FFFFFF;
        }

        td {
            color: #FFFFFF;
        }
        </style>
    """, unsafe_allow_html=True)

def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="CityRemit Assistant",
        page_icon="💼",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Apply dark theme
    apply_dark_theme()

    # Initialize session state
    initialize_session_state()

    # Create two columns: main content and monitoring panel
    main_col, debug_col = st.columns([2, 1])

    with main_col:
        # Application header
        st.title("💼 CityRemit Assistant")
        st.markdown("""
        Welcome to the **CityRemit Assistant**! You can ask questions about transaction details and customer information in natural language.

        **Examples:**
        - Show all transactions for customer John Smith.
        - What is the total amount of transactions in January 2024?
        - List the top 10 customers with the highest transaction amounts.
        - Find customers who made transactions over $1000.
        - Show me the latest transactions for customer ID 123.
        """)

        # Chat interface
        chat_container = st.container()

        # Input area
        with st.container():
            user_input = st.text_input(
                "Ask your question:",
                key="user_input",
                placeholder="e.g., Show all transactions for customer John Smith"
            )
            col1, col2 = st.columns([1, 5])
            with col1:
                send_button = st.button("Send", use_container_width=True)

        # Process input and update chat
        if send_button and user_input:
            try:
                # Log the question
                logger.info(f"Processing question: {user_input}")

                # Clear previous tool invocations
                tool_monitor.clear()

                # Get response from agent
                result = st.session_state.agent.run(user_input)

                # Format the response
                formatted_result = format_query_result(result)

                # Add to chat history
                st.session_state.chat_history.append({
                    "question": user_input,
                    "answer": formatted_result
                })

                # Clear input by rerunning the script
                st.rerun()  # Use st.rerun() instead of st.experimental_rerun()

            except Exception as e:
                logger.error(f"Error processing question: {str(e)}")
                st.error("Sorry, I encountered an error processing your request. Please try again.")

        # Display chat history (latest message at the bottom)
        with chat_container:
            for chat in st.session_state.chat_history:
                st.markdown("---")
                st.markdown(f'<div class="user-message">**You:** {chat["question"]}</div>',
                            unsafe_allow_html=True)
                st.markdown(f'<div class="assistant-message">**Assistant:** {chat["answer"]}</div>',
                            unsafe_allow_html=True)

    # Render monitoring panel in sidebar
    render_monitoring_panel()

    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #B2B2B2;'>
            <p>CityRemit Assistant powered by LangGraph and OpenAI</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()