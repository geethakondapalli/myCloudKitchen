import time
import streamlit as st
from psycopg2.extras import Json
import os
import re
from datetime import datetime
import uuid
from db_operations import get_pg_connection
from restaurant_config import *
from validators import *
from image_processing import extract_menu_from_image
import hashlib
import secrets
from caterer_operations import *
from orders_operations import *
from utils import extract_date_from_menu_id,menu_to_single_dataframe,format_datetime,date_converter,download_button_built_in,get_base64_image
from admin_operations import get_caterer_by_caterer_id
from templatecss import apply_custom_css
from profile_manager_ui import navigate_to,display_orders



def display_caterer_dashboard():
    """Display the caterer dashboard main page"""
    caterer_data = get_caterer_by_caterer_id(st.session_state.current_caterer_id)
    
    st.subheader("Dashboard")
    
    # Display quick stats and actions
    col1, col2 = st.columns(2,gap="medium")
    with col1:
      
        count=get_todays_orders_count(st.session_state.current_caterer_id) 

        if st.button(f"📋 **Today's Orders**", key="orders_count_button"):
        # Set query parameter and force rerun
            st.query_params["page"] = "order_summary_todaysdate"
            st.session_state.page="order_summary_todaysdate"
            st.rerun()
        # Display using the markdown component for HTML
        if st.button(f"📝 **Today's Delivery List**", key="delivery_addess_list_button"):
        # Set query parameter and force rerun
            st.query_params["page"] = "delivery_address_list"
            st.session_state.page="delivery_address_list"
            st.rerun()
            
       
    with col2:
        if st.button(f" ✅ **Orders to be Accepted**", key="pending_orders_button"):
        # Set query parameter and force rerun
            st.query_params["page"] = "acknowledge_todaysorders"
            st.session_state.page="acknowledge_todaysorders"
            st.rerun()
        if st.button(f"💰 **Total Earnings** ", key="total_earning_button"):
        # Set query parameter and force rerun
            st.query_params["page"] = "acknowledge_todaysorders"
            st.session_state.page="acknowledge_todaysorders"
            st.rerun()
    
    st.divider()

    # Quick access buttons
    st.subheader("Quick Actions")
    col1, col2 ,col3 = st.columns(3)
    with col1:
        if st.button("📋 View Orders", key="quick_orders"):
            st.query_params["page"] = "caterer_orders"
            st.session_state.page="caterer_orders"
            st.rerun()


    with col2:
        if st.button("✏️ View Payments", key="quick_payments"):
            st.query_params["page"] = "view_payments"
            st.session_state.page="view_payments"
            st.rerun()

    with col3:
        if st.button("✏️ Edit Profile", key="quick_profile"):
            st.query_params["page"] = "caterer_profile"
            st.session_state.page="caterer_profile"
            st.rerun()

    return True

def display_orders_to_accept():

    todaysdate=st.session_state.today_date
    userinfo=st.empty()
    orders=load_order_items(st.session_state.current_caterer_id, datetime.now(),status='pending')
    if not orders:
        with userinfo.container():
            st.info(f"No orders to be accepted for today {format_date(todaysdate)}")

        col1,col3 = st.columns([1, 4])
        with col1:
            selected_date = st.date_input(
                                "Select Date for Other Menus",
                                format="DD/MM/YYYY",
                    )
            print(f"Selected date :{selected_date}")
            selected_date_compare= selected_date.strftime('%Y-%m-%d')
            print(f"Todays date :{todaysdate}")
            print(f"Selected date compare :{selected_date_compare}")
            if(todaysdate!=selected_date_compare):
                userinfo.empty()

        orders=load_order_items(st.session_state.current_caterer_id, selected_date,status='pending')
        display_orders(orders,tab_name='pending')

    else :
        selected_date=todaysdate
        display_orders(orders,tab_name='pending')

    return

def display_delivery_address_list():
    
    todaysdate=st.session_state.today_date
    userinfo=st.empty()
    if not checkif_order_exists_for_selected_date(todaysdate):
        with userinfo.container():
            st.info(f"No orders found for today date {format_date(todaysdate)}")

        col1,col3 = st.columns([1, 4])
        with col1:
            selected_date = st.date_input(
                                "Select Date for Other Delivery Addresses List",
                                format="DD/MM/YYYY",
                    )
            print(f"Selected date :{selected_date}")
            selected_date_compare= selected_date.strftime('%Y-%m-%d')
            print(f"Todays date :{todaysdate}")
            print(f"Selected date compare :{selected_date_compare}")
            if(todaysdate!=selected_date_compare):
                userinfo.empty()

    else :
        selected_date=todaysdate

    orders_exists =checkif_order_exists_for_selected_date(selected_date_compare)
    delivery_address_list =get_delivery_address_list(selected_date)
    print(f"Delivery Address List: {delivery_address_list}") 
    if not orders_exists:
        with userinfo.container():
            st.info(f"No orders found for today date {format_date(selected_date)}")
            return# Debugging line
    if orders_exists and not delivery_address_list:
        st.info(f"All orders are pick up . No delivery address found for menu: {format_date(selected_date)}")
        return
    df = pd.DataFrame(delivery_address_list.copy())
    st.title(f"Delivery Addresses for Delivery Date:{format_date(selected_date)}")
    st.dataframe(df, use_container_width=True , hide_index=True)
    st.subheader('Download Options')
    download_button_built_in(df)

    if st.button("Find the Optimum Route for delivery", key="Optimum Route"):
        st.session_state.page = "optimum_route"
        st.rerun()

    return True

@st.fragment
def display_date_option():



    return order_sel_input

def display_order_summary_todays_orders():
    
    """Display all orders for the selected menu without using nested expanders"""
    todaysdate=st.session_state.today_date
    orders = load_orders_by_todaysdate(todaysdate)
    print(f"Orders: {orders}")  # Debugging line
    if not orders:
        st.info(f"No orders found for menu: {format_date(todaysdate)}")
        return
    # Process item data to create menu order summary
    menu_items_summary = {}
    
    # Iterate through all orders to collect item data
    for order in orders:
        if isinstance(order['items'], dict):
            for item_name, details in order['items'].items():
                if item_name not in menu_items_summary:
                    menu_items_summary[item_name] = {
                        "Item Name": item_name,
                        "Total Items Ordered": 0,
                        "Price": details['price']
                    }
                menu_items_summary[item_name]["Total Items Ordered"] += details['quantity']
    
    # Convert the summary to a list for DataFrame
    summary_items = list(menu_items_summary.values())
      # Also keep the original order summary for reference
    order_summaries = []
    total_sum_orders=0
    for order in orders:
        # Calculate number of items and quantity
        num_items = len(order['items']) if isinstance(order['items'], dict) else 0
        total_quantity = sum([item.get('quantity', 0) for item in order['items'].values()]) if isinstance(order['items'], dict) else 0
        total_sum_orders+=order['total']
        order_summaries.append({
            "Order ID": order['order_id'],
            "Customer": order['customer_name'],
            "Date": format_datetime(order['order_date']),
            "Total": f"£{order['total']:.2f}",
            "Status": order['status'].capitalize(),
            "Items": num_items,
            "Quantity": total_quantity
        })      

    df = pd.DataFrame(summary_items)
    columns_to_show = [col for col in df.columns if col != 'Price']
    display_df = df[columns_to_show]
    st.title("Items for Today's Menu")
    st.dataframe(display_df, use_container_width=True , hide_index=True)


    st.title("Todays Orders ")
    
    df = pd.DataFrame(order_summaries)
    st.dataframe(df, use_container_width=True , hide_index=True)    
    
    st.subheader("Today's Orders Summary")
    st.write(f"Total Customer Orders : {len(orders)}")
    st.markdown(f"**Total Revenue for the day : £{total_sum_orders}**")



