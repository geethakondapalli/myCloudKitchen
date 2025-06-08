import pandas as pd
from datetime import datetime
from restaurant_config import *
import streamlit as st
import io
import base64

# Function to convert extracted date to required format
def date_converter(extracted_date):
    #Menu Date: 2025-05-05
    # If extracted_date is already in YYYYMMDD format (e.g., '20250503')
    try :

        if extracted_date and len(extracted_date) == 8 and extracted_date.isdigit():
            # It's already in the right format, just use it directly
            date_str = extracted_date
        else:
            # Try to parse the date in other formats
            try:
                for date_format in date_formats:
                    try:
                        parsed_date = datetime.strptime(extracted_date, date_format)
                        date_str = parsed_date.strftime('%d%m%Y')
                        break
                    except ValueError:
                        continue
                else:
                    # If none of the formats worked, use today
                    date_str = datetime.now().strftime('%d%m%Y')
            except:
                date_str = datetime.now().strftime('%d%m%Y')

    except ValueError:
        # Fallback to today's date
        st.warning(f"Could not parse date: {extracted_date}")
    
    return date_str
    
def download_button_built_in(df):
    csv = df.to_csv(index=False)
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    excel_data = excel_buffer.getvalue()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="data.csv",
            mime="text/csv"
        )
    
    with col2:
        st.download_button(
            label="Download Excel",
            data=excel_data,
            file_name="data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        st.error(f"Image not found: {image_path}")
        return None
    
# Function to format date
def format_date(date_obj):
    """Format date as DD-MMM-YYYY"""
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.strptime(date_obj, "%Y-%m-%d").date()
        except:
            return date_obj
            
    if hasattr(date_obj, 'strftime'):
        return date_obj.strftime("%d-%b-%Y")
    return str(date_obj)

# Function to format datetime
def format_datetime(dt_obj):
    """Format datetime as DD-MMM-YYYY HH:MM"""
    if isinstance(dt_obj, str):
        try:
            dt_obj = datetime.strptime(dt_obj, "%Y-%m-%d %H:%M:%S")
        except:
            return dt_obj
            
    if hasattr(dt_obj, 'strftime'):
        return dt_obj.strftime("%d-%b-%Y %H:%M")
    return str(dt_obj)

def extract_date_from_menu_id(menu_id):
    """
    Extracts and formats the date from a menu_id in format M26042025.
    Returns the date formatted as DD-MMM-YYYY (e.g., 26-APR-2025).
    
    Args:
        menu_id (str): Menu ID in format M26042025
        
    Returns:
        str: Formatted date string or None if invalid format
    """
    try:
        # Validate the menu_id format
        if not menu_id or not isinstance(menu_id, str) or not menu_id.startswith('M'):
            return None
            
        # Extract the date portion (assuming it follows 'M')
        date_str = menu_id[1:]
        
        # Check if we have the expected 8 digits
        if len(date_str) != 8 or not date_str.isdigit():
            return None
            
        # Parse day, month, year
        day = date_str[0:2]
        month = date_str[2:4]
        year = date_str[4:8]
        
        # Convert month number to month name abbreviation
        month_names = {
            '01': 'JAN', '02': 'FEB', '03': 'MAR', '04': 'APR', 
            '05': 'MAY', '06': 'JUN', '07': 'JUL', '08': 'AUG',
            '09': 'SEP', '10': 'OCT', '11': 'NOV', '12': 'DEC'
        }
        
        # Format the date
        if month in month_names:
            formatted_date = f"{day}-{month_names[month]}-{year}"
            return formatted_date
        else:
            return None
            
    except Exception as e:
        print(f"Error extracting date from menu_id: {e}")
        return None

def menu_to_single_dataframe(menu_data):
    """
    Convert menu data to a single pandas DataFrame with menu info repeated for each item.
    
    Args:
        menu_data (dict): The menu data dictionary from the database
        
    Returns:
        pd.DataFrame: DataFrame containing all menu items with menu info
    """
    try:
        # Create a DataFrame for the menu items
        items_df = pd.DataFrame(menu_data['items'])
        
        # Extract other menu information (excluding the items list)
        menu_info = {k: v for k, v in menu_data.items() if k != 'items'}
        
        # Add menu info columns to each row in items_df
        for key, value in menu_info.items():
            items_df[key] = value
        
        return items_df
        
    except Exception as e:
        print(f"Error converting menu to DataFrame: {e}")
        return None
