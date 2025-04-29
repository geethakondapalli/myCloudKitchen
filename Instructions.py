    # Add info about Google Sheets setup
import streamlit as st
from restaurant_config import RESTAURANT_CONFIG, ADMIN_CONFIG
# Set up Streamlit page
st.set_page_config(page_title=f"{RESTAURANT_CONFIG['name']} - Admin-Setup Details ")
st.header("👩‍💼 Welcome to Admin Panel - Set up Details")   

with st.expander("ℹ️ Setup Instructions"):
        st.markdown("""
        ### Google Sheets Setup:
        1. Create a service account in Google Cloud Console
        2. Share your Google Sheets with the service account email
        3. Add the service account credentials to Streamlit secrets.toml file:
        ```
        [gcp_service_account]
        type = "service_account"
        project_id = "your-project-id"
        private_key_id = "your-private-key-id"
        private_key = "your-private-key"
        client_email = "your-service-account-email"
        client_id = "your-client-id"
        auth_uri = "https://accounts.google.com/o/oauth2/auth"
        token_uri = "https://oauth2.googleapis.com/token"
        auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
        client_x509_cert_url = "your-cert-url"
        ```
        """)