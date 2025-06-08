import time
import streamlit as st
from psycopg2.extras import Json
import os
import re
from datetime import datetime
import uuid
from db_operations import get_pg_connection
from restaurant_config import *
from validators import validate_name, validate_phone, validate_email
from image_processing import extract_menu_from_image
import hashlib
import secrets
from caterer_operations import *
from orders_operations import *
from utils import extract_date_from_menu_id,menu_to_single_dataframe,format_datetime,date_converter,download_button_built_in
from admin_operations import get_caterer_by_caterer_id
from templatecss import apply_custom_css
from paymentgateway import *
import stripe


# Initialize session state
def initialize_session_state():
    if 'customer_validated' not in st.session_state:
        st.session_state.customer_validated = False
    if 'order_validated' not in st.session_state:
        st.session_state.order_validated = False
    if 'delivery_selected' not in st.session_state:
        st.session_state.delivery_selected = False
    if 'payment_validated' not in st.session_state:
        st.session_state.payment_validated = False

# Validation functions
def validate_customer_info(name, email, phone,invoicereq):
    errors = []
    if not name or len(name.strip()) < 3:
        errors.append("Name must be at least 3 characters")
    
    if not phone or len(phone) < 10:
        errors.append("Valid phone number is required")

    if invoicereq:
        if not email or "@" not in email:
            errors.append("Valid email is required")

    return len(errors) == 0, errors

def validate_order_items(items):
    if not items or len(items) == 0:
        return False, ["Please select at least one item"]
    total = sum(details['price'] * details['quantity'] for details in items.values())
    if total <= 0:
        return False, ["Order total must be greater than 0"]
    return True, []


def display_customer_order_page():

    if not st.session_state.session_id :
        params = st.query_params
        menu_id = params["menu_id"] if "menu_id" in params else None
        st.session_state.menu_id=menu_id
        payment_status="Payment Pending"
        valid_order=False
        print(f"Menu ID: {menu_id}")
        # --- CUSTOMER ORDER MODE ---
        st.header(f"{RESTAURANT_CONFIG['emoji']} {RESTAURANT_CONFIG['name']} — Place the order")
        initialize_session_state()

        menu = load_menu_from_db(menu_id)
        menu_df = menu_to_single_dataframe(menu)
        # Progress indicator
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Customer Info", "✅" if st.session_state.customer_validated else "⏳")
        with col2:
            st.metric("Order Items", "✅" if st.session_state.order_validated else "⏳")
        with col3:
            st.metric("Delivery Method", "✅" if st.session_state.delivery_selected else "⏳")
        with col4:
            st.metric("Payment", "✅" if st.session_state.payment_validated else "⏳")
        
        st.divider()
        
        if not menu_df.empty:
            # Customer name with immediate validation
            customer_name = st.text_input("Enter Your Name *", placeholder="Full Name" , key="customer_name")

            name_valid, name_error = validate_name(customer_name)
            print (f"name_valid is {name_valid}")
            if customer_name and name_valid is False:
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


            if customer_name or customer_email or customer_phone:
                is_valid, errors = validate_customer_info(customer_name, customer_email, customer_phone,need_invoice)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    st.success("✅ Customer information valid")
                    st.session_state.customer_validated = True

            st.subheader("Menu Items for " + extract_date_from_menu_id(menu_id))
            order = {}
            
            for index, row in menu_df.iterrows():
                qty = st.number_input(
                    f"{row['item_name']} ({RESTAURANT_CONFIG['currency']}{row['price']:.2f})", 
                    min_value=0, 
                    step=1, 
                    key=index
                )
                if qty > 0:
                    order[row['item_name']] = {"price": row['price'], "quantity": qty}
            
            # Validate order
                is_valid, errors = validate_order_items(order)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    st.session_state.order_validated = True
            
            if not st.session_state.order_validated:
                st.info("Please select items to proceed")
                return

            # Calculate and display total
            total = sum(details['price'] * details['quantity'] for details in order.values())
            st.subheader(f"Total: {RESTAURANT_CONFIG['currency']}{total:.2f}")

            
            delivery_method = st.radio(
                "Choose delivery method:",
                ["Pickup Order", "Home Delivery"],
                horizontal=True
            )
            if delivery_method:
                st.session_state.delivery_selected = True

            # Show different inputs and information based on selection
            if delivery_method == "Home Delivery":
                # Display delivery fee information
                if  "delivery_fee" not in st.session_state:
                    st.session_state.delivery_fee = 5
                if total >= 20:
                    st.session_state.delivery_fee = 0
                    st.info(f"Yay!! Your Order is now for Free Delivery.")
                else: 
                    st.session_state.delivery_fee = 5
                    st.info(f"Delivery Fee: {RESTAURANT_CONFIG['currency']}{st.session_state.delivery_fee:.2f}")

                total+= st.session_state.delivery_fee
                # Collect address for delivery
                #Address line 1
                address_line1 = st.text_input(
                    "House number/name and street",
                    placeholder="e.g. 10 Downing Street",
                    help="Enter your house number/name and street"
                )

                # Address line 2 (optional)
                address_line2 = st.text_input(
                    "Address line 2 (optional)",
                    placeholder="e.g. Flat 3, Building name",
                    help="Additional address information if needed"
                )

                # City/Town
                city = st.text_input(
                    "Town/City",
                    placeholder="e.g. London",
                    help="Enter your town or city"
                )

                # County (optional in UK addresses)
                county = st.text_input(
                    "County (optional)",
                    placeholder="e.g. Greater London",
                    help="County is optional for UK addresses"
                )

                # Postcode - UK format
                postcode = st.text_input(
                    "Postcode",
                    placeholder="e.g. SW1A 2AA",
                    help="Enter your UK postcode"
                )
                
                customer_address = {
                    "address_line1": address_line1,
                    "address_line2": address_line2,
                    "city": city,
                    "county": county,
                    "postcode": postcode
                }

                # Validate address field
                if 'submit_order' in st.session_state and st.session_state.submit_order:
                    if not address_line1 and city and postcode:
                        st.error("Please fill in required fields: House number/street, Town/City, and Postcode")
                
            else:  # Pickup
                # Display pickup information
                pickup_address = "28 Redmason Road, Ardleigh,CO77SW"
                st.info(f"Pickup location: {pickup_address} \n Please collect your order at the scheduled time.")
                
                # No delivery fee
                customer_address = {
                    "address_line1":"Picking up from restaurant"
                }  # Set a default value
            
            # Special instructions
            special_instructions = st.text_area("Special Instructions (optional)")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.subheader(f"Total : {RESTAURANT_CONFIG['currency']}{total:.2f}")

            order_info = {
                    "timestamp": timestamp,
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_phone": customer_phone,
                    "customer_address": customer_address,
                    "menu_date": extract_date_from_menu_id(menu_id),
                    "menu_id":menu_id,
                    "special_instructions": special_instructions
                }

            with st.expander("Payment details ") :

                st.subheader("Bank Transfer Details")
                st.info("Please transfer the amount to the following bank account and confirm seller:")
                st.code("""
                Bank: Example Bank
                Account Name: Our Online Shop
                Account Number: 1234567890
                Routing Number: 987654321
                Reference: YOUR-ORDER-ID-NAME
                """)
            st.session_state.payment_status="Payment Pending"
            payment_mode="Bank Transfer"
        if st.button("Submit Order", type="primary", key="submit_order_button"):
            result= save_order_db(order, order_info, menu_id,payment_mode,payment_status)
            print(f"Order ID: {result['order_id']}")
            print(f"Status: {result['status']}")             
            if result['status'] == "saved":
                st.success("✅ Order Submitted Successfully! Thank you!")   
                # Display order summary
                st.subheader("Order Summary")
                total = 0
                for item, details in order.items():
                    item_total = details['price'] * details['quantity']
                    total += item_total
                    st.write(f"• {item} x {details['quantity']} = {RESTAURANT_CONFIG['currency']}{item_total:.2f}")
                st.write(f"**Total: {RESTAURANT_CONFIG['currency']}{total:.2f}**")
            else:
                st.error("Error saving order. Please contact admin")
                    
        
@st.fragment
def order_submit(order, order_info, menu_id,payment_mode,payment_status,valid_order):

#   Implement this function , when Pay Online is implemented
   return True



def display_payment_popup(total_amount,payment_mode):    

    payment_container = st.empty()
    transaction_reference= None
    valid_order=False
    payment_status="Payment Pending"
    failure_response=""
    if payment_mode=='online' :
        # Create a popup using st.dialog
        with payment_container.container():
            payment_gateway="mock1"
            payment_response="mockresponse1"
            
            st.subheader("Pay Online") 
        
        col_buttons = st.columns([1, 1])
            
        with col_buttons[0]:
             
            current_url = ADMIN_CONFIG['base_url']
            success_url = f"{current_url}/?session_id={{CHECKOUT_SESSION_ID}}"
            cancel_url = f"{current_url}/?cancelled=true"
            session = create_checkout_session(
                price_amount=total_amount,
                service_name="customer_id",
                success_url=success_url,
                cancel_url=cancel_url
            )
            print(f"checkout session :{session}")
            if session and session.url:
                st.markdown(
                    f"""
                    <a href="{session.url}" target="_blank">
                        <button>Go to Payment</button>
                    </a>
                    """,
                    unsafe_allow_html=True
                )

            print(f"Transaction reference :{transaction_reference}")
            if transaction_reference !="":
                st.success("Order Can be submitted")
                valid_order=True
                payment_status="Payment Success"
                st.balloons()
        
            else :
                st.info("Enter Transaction Reference")
        
                payment_info = {
                "payment_method": payment_mode,
                "payment_status": payment_status,
                "transaction_reference": transaction_reference,
                "payment_gateway": payment_gateway,
                "payment_response": payment_response,
                "failure_response": failure_response
            }

        with col_buttons[1]:
                if st.button("Cancel", key="cancel_button"):
                    valid_order=False
                    payment_status="Payment Failed"
                    payment_container.empty()  # Clear the payment form

                print(f"Function :Payment status ,{payment_status}")
                print(f"Function :Valid Order ,{valid_order}")         

        return {'payment_status':payment_status,'valid_order':valid_order}

    else :
        with payment_container.container():
            st.subheader("Bank Transfer Details")
            st.info("Please transfer the amount to the following bank account:")
            st.code("""
            Bank: Example Bank
            Account Name: Our Online Shop
            Account Number: 1234567890
            Routing Number: 987654321
            Reference: YOUR-ORDER-ID
            """)
            transaction_reference=st.text_input("Transaction Reference Number (after you complete the transfer)")

    bank_transfer_payment = st.columns([1, 1])
            
    with bank_transfer_payment[0]:
        if st.button("Bank Tranfer", key="bank_transfer"):
            if not transaction_reference:
                st.info("Transaction Reference is None . Please make sure you do bank transfer and confirm the seller")
            valid_order=True
            payment_status="Payment Pending"
        
               
    with bank_transfer_payment[1]:
        if st.button("Cancel", key="cancel_button_bank_transfer"):
            valid_order=False
            payment_status="Payment Failed"
            payment_container.empty()  # Clear the payment form

    print(f"Function :Payment status ,{payment_status}")
    print(f"Function :Valid Order ,{valid_order}")         

    return {'payment_status':payment_status,'valid_order':valid_order}
    