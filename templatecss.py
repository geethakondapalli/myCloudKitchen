import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

def apply_custom_css():
    """Apply custom CSS for modern design"""
    st.markdown("""
    <style>
    /* Main container styling */
    .main {
        padding-top: 1rem;
    }
    
    /* Custom header styling */
    .custom-header {
        background: linear-gradient(135deg, #6c7b7f, #495057, #2c3e50);
        padding: 2rem;
        border-radius: 5px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    
    /* custom header h1 */
                
    .custom-header h1 {
    margin: 0;
    font-size: 2.5rem;
    font-weight: bold;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    /* Logo at sidebar */
    
    .sidebar-logo {
    display: block;
    margin-top: 0;
    margin-right: auto;
    margin-bottom: 1rem;
    margin-left: 0;
    border-radius: 10px;
    width: 150px;
    height: auto;
    }
                
    /* Card styling */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8a39d;
    }
    
    /* sidebar Divider */
                
    div[data-testid="stSidebar"] hr {
    border: none;
    height: 10px;
    background: linear-gradient(90deg, transparent, #f39c12, transparent);
    margin: 1.5rem 0;
    border-radius: 2px;
    }
                
    /* Column Styling */
                
    .column-container {
    background-color: #fafafa;
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #e0e0e0;
    margin: 0.5rem 0;
    }

                

    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #6c7b7f, #495057, #2c3e50);
        color: white;
        border: none;
        border-radius: 20px;
        padding: 0.5rem 2rem;
        font-weight: bold;
    }
                
    .stButton > button:hover {
    background: linear-gradient(135deg, #495057, #2c3e50, #1a252f) !important;
    transform: translateY(-2px) !important;
    transition: all 0.3s ease !important;
    }

    .stButton > button:active {
        transform: translateY(0px) !important;
    }
    
    /* Success message styling */
    .success-message {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    /* Warning message styling */
    .warning-message {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)
