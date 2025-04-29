import streamlit as st
import pandas as pd
from PIL import Image
import io
import re
from datetime import datetime
import os
from urllib.parse import urlencode
import gspread
from google.oauth2 import service_account
from gspread_dataframe import set_with_dataframe
from restaurant_config import RESTAURANT_CONFIG, ADMIN_CONFIG
from validators import validate_name, validate_phone, validate_email
from image_processing import extract_menu_from_image
from gsheets_processing import load_menu_from_sheets, save_menu_to_sheets, save_order_to_sheets


date_formats = [
    '%d/%m/%Y',       # 23/04/2025
    '%m/%d/%Y',       # 04/23/2025
    '%d-%m-%Y',       # 23-04-2025
    '%m-%d-%Y',       # 04-23-2025
    '%B %d, %Y',      # April 23, 2025
    '%d %B %Y',       # 23 April 2025
    '%d-%b-%y',       # 1-APR-25 (this is the one you need)
    '%d-%b-%Y',       # 1-APR-2025
    '%d/%b/%y',       # 1/APR/25
    '%d/%b/%Y'        # 1/APR/2025
]
# Set up Streamlit page
st.set_page_config(page_title=f"{RESTAURANT_CONFIG['name']} - Admin & Order Form")


# Read query parameters
params = st.query_params
menu_id = params["menu_id"] if "menu_id" in params else None

st.title(f"{RESTAURANT_CONFIG['emoji']} {RESTAURANT_CONFIG['name']}")

# --- ADMIN MODE ---
if menu_id is None:
    st.header("👩‍💼 Welcome to Admin Panel - Upload Menu Here")
    


    uploaded_image = st.file_uploader("Upload Menu Image", type=["png", "jpg", "jpeg"])

    if uploaded_image:
        image = Image.open(uploaded_image)
        st.image(image, caption="Uploaded Menu", use_column_width=True)

        menu_df, extracted_date, ocr_success = extract_menu_from_image(image)
        print(f"Extracted Date: {extracted_date}")

        if ocr_success:
            st.success("Menu Extracted Successfully!")
            
            # Initialize session state for menu dataframe if it doesn't exist
            if 'menu_df' not in st.session_state:
                display_df = menu_df.copy()
                display_df.insert(0, "Serial", range(1, len(menu_df) + 1))
                st.dataframe(
                    display_df,
                    hide_index=True,  # Hide the original index
                    column_config={
                        "Serial": st.column_config.NumberColumn("No."),
                        "Item": st.column_config.TextColumn("Menu Item"),
                        "Price": st.column_config.NumberColumn("Price", format="£%.2f"),
                    }
                )
            else:
                # Use the existing menu dataframe if it was already extracted
                menu_df = st.session_state.menu_df        
            # Add option to add more items
            st.subheader("Add More Items , If Needed")
            # Allow manual editing of the menu
            st.subheader("Edit Menu (if needed)")
            edited_df = st.data_editor(
                menu_df,
                num_rows="dynamic",
                column_config={
                    "Item": st.column_config.TextColumn("Menu Item", required=True),
                    "Price": st.column_config.NumberColumn(
                        f"Price ({RESTAURANT_CONFIG['currency']})", 
                        min_value=0, 
                        format=f"{RESTAURANT_CONFIG['currency']}%.2f",
                        required=True
                    )
                },
                hide_index=True
            )

            try:
            # Parse the extracted date string
                # If extracted_date is already in YYYYMMDD format (e.g., '20250503')
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

            # Use it in the date picker
            extracted_date_obj = datetime.strptime(date_str, "%d%m%Y").date()
            menu_date_input = st.date_input(
                    "Menu Date",
                    value=extracted_date_obj,
                    format="DD/MM/YYYY",
            )

            if st.button("Save Menu & Generate Link"):

                # Create menu ID with date and timestamp
                timestamp = str(int(datetime.now().timestamp()))[-6:]  # Last 6 digits for uniqueness
                menu_id = f"{date_str}_{timestamp}"
                try:

                    base_url = "http://localhost:8509"  # Change this to your deployed URL
                    order_link = f"{base_url}?menu_id={menu_id}"

                    sheet_url = save_menu_to_sheets(edited_df, menu_id,order_link,extracted_date_obj)
                    
                    st.success("✅ Order Form Link Generated!")
                    st.markdown(f"[🔗 Click Here to View Order Form]({order_link})")
                    st.code(order_link)
                    
                    st.markdown(f"[📊 View Menu in Google Sheets]({sheet_url})")
                except Exception as e:
                    st.error(f"Error saving to Google Sheets: {str(e)}")
                    st.info("Make sure you've set up the Google Sheets API credentials correctly.")

# --- CUSTOMER ORDER MODE ---
else:
    st.header("🛒 Place Your Order")

    try:
        menu_df, menu_date_obj, menu_date_str = load_menu_from_sheets(menu_id)
        
        if not menu_df.empty:
            # Customer name with immediate validation
            customer_name = st.text_input("Enter Your Name*", placeholder="Full Name")
            name_valid, name_error = validate_name(customer_name)
            if customer_name and not name_valid:
                st.error(name_error)
            
            # Phone with immediate validation
            customer_phone = st.text_input("Enter Your Phone Number*", placeholder="e.g. 07XXXXXXXXX")
            phone_valid, phone_error = validate_phone(customer_phone)
            if customer_phone and not phone_valid:
                st.error(phone_error)
           # Invoice option
            need_invoice = st.checkbox("I need an invoice for this order")

            # Email with immediate validation 
            customer_email = st.text_input(
                "Enter Your Email" + (" *" if need_invoice else " (optional)"), 
                placeholder="email@example.com"
            )
            email_valid, email_error = validate_email(customer_email, required=need_invoice)
            if customer_email and not email_valid:
                st.error(email_error)

            st.success("Menu Loaded Successfully!")

            st.subheader("Menu Items for " + menu_date_str)
            order = {}
            
            for index, row in menu_df.iterrows():
                qty = st.number_input(
                    f"{row['Item']} ({RESTAURANT_CONFIG['currency']}{row['Price']:.2f})", 
                    min_value=0, 
                    step=1, 
                    key=index
                )
                if qty > 0:
                    order[row['Item']] = {"price": row['Price'], "quantity": qty}

            # Calculate and display total
            total = sum(details['price'] * details['quantity'] for details in order.values())
            st.subheader(f"Total: {RESTAURANT_CONFIG['currency']}{total:.2f}")
            
            # Special instructions
            special_instructions = st.text_area("Special Instructions (optional)")

            if st.button("Submit Order"):
                if not customer_name:
                    st.warning("Please enter your name.")
                elif not order:
                    st.warning("Please select at least one item.")
                else:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    try:
                        # Prepare order information for saving
                        order_info = {
                            "timestamp": timestamp,
                            "customer_name": customer_name,
                            "customer_email": customer_email,
                            "customer_phone": customer_phone,
                            "special_instructions": special_instructions
                        }
                        
                        sheet_url = save_order_to_sheets(order, order_info, menu_id)
                        st.success("✅ Order Submitted Successfully! Thank you!")
                        
                        # Display order summary
                        st.subheader("Order Summary")
                        total = 0
                        for item, details in order.items():
                            item_total = details['price'] * details['quantity']
                            total += item_total
                            st.write(f"• {item} x {details['quantity']} = {RESTAURANT_CONFIG['currency']}{item_total:.2f}")
                        st.write(f"**Total: {RESTAURANT_CONFIG['currency']}{total:.2f}**")
                        
                    except Exception as e:
                        st.error(f"Error saving order: {str(e)}")
        else:
            st.error("Menu not found or is empty.")

    except Exception as e:
        st.error(f"Error: {str(e)}")

