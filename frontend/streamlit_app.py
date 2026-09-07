import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(layout="wide", page_title="V-CAD | 3D ULPIN")

# Hide Streamlit's default padding to make the UI full-screen
st.markdown("""
    <style>
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {
            padding-top: 0rem;
            padding-bottom: 0rem;
            padding-left: 0rem;
            padding-right: 0rem;
            max-width: 100%;
        }
        iframe {
            display: block;
            border: none;
            height: 100vh !important;
            width: 100vw !important;
        }
    </style>
""", unsafe_allow_html=True)

# Get the directory of this python file
base_dir = Path(__file__).parent

# Read the teammate's new consolidated HTML and config files
html = (base_dir / "index.html").read_text(encoding="utf-8")
config = (base_dir / "config.js").read_text(encoding="utf-8")

# Inject config.js directly into the HTML
html = html.replace('<script src="config.js"></script>', f'<script>{config}</script>')

# Render the frontend
components.html(html, height=1200, scrolling=True)
