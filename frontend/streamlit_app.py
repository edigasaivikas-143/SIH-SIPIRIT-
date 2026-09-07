import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(layout="wide")

# Hide Streamlit's default chrome and padding to make the iframe full-screen
st.markdown("""
    <style>
        /* Hide the top header bar */
        header {visibility: hidden;}
        /* Hide the bottom footer */
        footer {visibility: hidden;}
        /* Remove padding from the main block */
        .block-container {
            padding-top: 0rem;
            padding-bottom: 0rem;
            padding-left: 0rem;
            padding-right: 0rem;
            max-width: 100%;
        }
        /* Remove padding from the component wrapper */
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

# Read the teammate's web files
html = (base_dir / "index.html").read_text(encoding="utf-8")
css = (base_dir / "styles.css").read_text(encoding="utf-8")
js = (base_dir / "app.js").read_text(encoding="utf-8")
config = (base_dir / "config.js").read_text(encoding="utf-8")

# Inject CSS and JS directly into the HTML 
html = html.replace('<link rel="stylesheet" href="styles.css">', f'<style>{css}</style>')
html = html.replace('<script src="config.js"></script>', f'<script>{config}</script>')
html = html.replace('<script src="app.js"></script>', f'<script>{js}</script>')

# Render the combined frontend
components.html(html, height=1200, scrolling=True)
