import json
import streamlit as st
import os

def load_config():
    """Load configuration from config.json file."""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load configuration: {e}")
        return {}

def reload_config():
    """Reload configuration and update session state."""
    if 'config' in st.session_state:
        st.session_state.config = load_config()
    return st.session_state.config