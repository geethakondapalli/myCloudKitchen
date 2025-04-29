import gspread
from restaurant_config import RESTAURANT_CONFIG, ADMIN_CONFIG
import streamlit as st
from google.oauth2 import service_account
from datetime import datetime
import pandas as pd


# Google Sheets Configuration
def connect_to_gsheets():
    """Connect to Google Sheets API"""
    # Create a connection object
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    gc = gspread.authorize(credentials)
    return gc

def load_menu_from_sheets(menu_id):
    """Load menu data from Google Sheets"""
    gc = connect_to_gsheets()
    menu_sheet_name = f"{RESTAURANT_CONFIG['sheets_prefix']}_Menus"
    print(f"Loading menu from sheet: {menu_sheet_name}, worksheet: menu_{menu_id}")
    try:
        sheet = gc.open(menu_sheet_name)
        worksheet = sheet.worksheet(f"menu_{menu_id}")
        
        # Extract the menu date first
        menu_date_obj, menu_date_str = get_menu_date_from_sheet(worksheet)

        # Get all values as a list of lists
        all_values = worksheet.get_all_values()
        
        # Skip the first two rows (index 0 and 1) and use the fourth row (index 3) as header
        if len(all_values) >= 3:
            headers = all_values[3]  # Fourth row (index 3)
            data_rows = all_values[4:]  # Fifth row (index 4) and beyond
            
            records = worksheet.get_all_records(head=4) 
            print(f"Loaded {len(records)} records from menu_{menu_id}")
    
            # Convert to DataFrame
            df = pd.DataFrame(records)
        
            # Add the menu date to the returned data
            return df, menu_date_obj, menu_date_str
        else:
            return pd.DataFrame(), None, None
    
    except Exception as e:
        print(f"Error loading menu from sheets: {str(e)}")
        return pd.DataFrame(), None, None

        return df
   
    except (gspread.SpreadsheetNotFound, gspread.WorksheetNotFound) as e:
        st.error(f"Menu not found. Please upload a menu first. Error: {str(e)}")
        return pd.DataFrame()

def get_menu_date_from_sheet(worksheet):
    """Extract the menu date from cell B2 in the worksheet"""
    try:
        # Get the value from cell B2 (row 2, column 2)
        date_cell = worksheet.cell(2, 2).value
        
        # If the cell exists and has a value
        if date_cell:
            # Try to parse it as a date (assuming format "DD-MMM-YYYY" like "01-APR-2025")
            try:
                # Parse the date string back to a datetime object
                date_obj = datetime.strptime(date_cell, "%d-%b-%Y")
                return date_obj, date_cell  # Return both datetime object and original string
            except ValueError:
                # If parsing fails, return the raw string
                return None, date_cell
        
        # If cell is empty or doesn't exist
        return None, None
    
    except Exception as e:
        print(f"Error retrieving menu date: {str(e)}")
        return None, None

def save_order_to_sheets(order_items, order_info, menu_id):
    """Save order data to Google Sheets with each item as a separate row"""
    gc = connect_to_gsheets()
    sheet_name = f"orders_{menu_id}"
    orders_sheet_name = f"{RESTAURANT_CONFIG['sheets_prefix']}_Orders"
    
    # Try to open existing sheet, create if it doesn't exist
    try:
        sheet = gc.open(orders_sheet_name)
    except gspread.SpreadsheetNotFound:
        sheet = gc.create(orders_sheet_name)
    
    # Check if worksheet for this menu exists
    try:
        worksheet = sheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        # Create new worksheet with headers
        headers = [
            "Order ID",
            "Timestamp", 
            "Customer Name", 
            "Customer Email", 
            "Customer Phone", 
            "Item Name",
            "Item Price",
            "Quantity",
            "Item Total(£)",
            "Special Instructions"
        ]
        worksheet = sheet.add_worksheet(title=sheet_name, rows=1, cols=len(headers))
        worksheet.append_row(headers)
    
    
    # Create a unique order ID
    order_id = f"{menu_id}_{order_info['customer_name']}"
    
    # Add each item as a separate row
    rows_to_add = []
    for item_name, details in order_items.items():
        item_row = [
            order_id,
            order_info["timestamp"],
            order_info["customer_name"],
            order_info["customer_email"],
            order_info["customer_phone"],
            item_name,
            details["price"],
            details["quantity"],
            details["price"] * details["quantity"],
            order_info["special_instructions"]
        ]
        rows_to_add.append(item_row)
    
    # Append all rows at once (more efficient)
    if rows_to_add:
        worksheet.append_rows(rows_to_add)
    
    return sheet.url

def save_menu_to_sheets(menu_df, menu_id,order_link ,menu_date_obj):

    """Save menu data to Google Sheets"""
    gc = connect_to_gsheets()
    sheet_name = f"menu_{menu_id}"
    menu_sheet_name = f"{RESTAURANT_CONFIG['sheets_prefix']}_Menus"
    st.write(f"Saving menu to sheet: {menu_sheet_name}, worksheet: {sheet_name}")
    
    # Try to open existing sheet, create if it doesn't exist
    try:
        sheet = gc.open(menu_sheet_name)
        print(f"Spreadsheet opened successfully!")
       
    except gspread.SpreadsheetNotFound:
        sheet = gc.create(menu_sheet_name)
        st.success("Spreadsheet created successfully!")
        st.write(f"Saving menu to sheet: {sheet.url}, worksheet: {sheet_name}")
        
        # Optionally share the sheet with specific users
        # sheet.share('example@gmail.com', perm_type='user', role='writer')
        # Share with the client_email from service account
        service_account_email = st.secrets["gcp_service_account"]["client_email"]
        
        # Also share with any admin emails if configured
        try:
            # Try to get as a list first
            admin_emails = ADMIN_CONFIG.get("admin_emails", [])
            
            # If it's a single string, convert to list
            if isinstance(admin_emails, str) and "@" in admin_emails:
                admin_emails = [admin_emails]
                
            # Also check for a single admin_email field
            admin_email = ADMIN_CONFIG.get("admin_email", "")
            if admin_email and "@" in admin_email and admin_email not in admin_emails:
                admin_emails.append(admin_email)
                
            # Share with each admin email
            for email in admin_emails:
                if email and "@" in email:
                    sheet.share(email, perm_type='user', role='writer')
                    st.info(f"Shared sheet with {email}")
        except Exception as e:
            st.warning(f"Error sharing sheet: {str(e)}")
    
    # Create a new worksheet for this menu
    try:
        worksheet = sheet.add_worksheet(title=sheet_name, rows=len(menu_df)+ 10, cols=len(menu_df.columns))
    except gspread.exceptions.APIError:
        # Worksheet already exists, get it
        worksheet = sheet.worksheet(sheet_name)
        # Clear existing content
        worksheet.clear()
    

    # Add the order link in a separate section at the top
    worksheet.update_cell(1, 1, "Order Form URL:")
    worksheet.update_cell(1, 2, order_link)

     # Make the URL clickable
    worksheet.format("B1", {"textFormat": {"underline": True, "bold": True}})

    worksheet.update_cell(2, 1, "Menu Date:")
    worksheet.update_cell(2, 2, menu_date_obj.strftime("%d-%b-%Y"))
    
    # Add a blank row as a separator
    # Now write the menu data starting from row 3
    header_row = [list(menu_df.columns)]
    data_rows = menu_df.values.tolist()
    all_rows = header_row + data_rows
    
    # Update the data range starting from row 4
    cell_range = f'A4:{chr(65 + len(menu_df.columns) - 1)}{4 + len(menu_df)}'
    worksheet.update(all_rows,cell_range)
    
    return sheet.url