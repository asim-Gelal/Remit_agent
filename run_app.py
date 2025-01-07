"""Entry point for the Streamlit application."""

import streamlit.web.bootstrap
from Remit_agent.ui.streamlit_app import main

if __name__ == "__main__":
    streamlit.web.bootstrap.run("Remit_agent.ui.streamlit_app", "", [], [])