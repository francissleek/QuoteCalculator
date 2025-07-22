import json
import streamlit as st

def load_config(file_path='config.json'):
    try:
        if "config" in st.secrets:
            return json.loads(st.secrets["config"])
    except Exception:
        pass
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading config: {e}")
        st.stop()