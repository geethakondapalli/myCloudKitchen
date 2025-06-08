import time
import streamlit as st
from psycopg2.extras import Json
import os
import re
from datetime import datetime
import uuid
from db_operations import get_pg_connection
from restaurant_config import *
from PIL import Image
from validators import *
from image_processing import extract_menu_from_image
import hashlib
import secrets
from caterer_operations import *
from orders_operations import *
from utils import extract_date_from_menu_id,menu_to_single_dataframe,format_datetime,date_converter,download_button_built_in,get_base64_image
from admin_operations import get_caterer_by_caterer_id
from templatecss import apply_custom_css


# Configuration
APP_NAME = "CaterCloud - A Cloud Kitchen Platform"
POSTGRES_CONFIG = {
    "host": "localhost",
    "database": "catercloud",
    "user": "postgres",
    "password": "postgres",
    "port": 5432
}

# Cache refresh interval in seconds
CACHE_REFRESH_INTERVAL = 300  # 5 minutes

def navigate_to(pagename):
    st.query_params["page"] = pagename
    st.session_state.page=pagename

def create_default_admin():
    """Create default admin user if not exists"""
    with get_pg_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = 'admin@catercloud.com'")
        result = cursor.fetchone()
        
        if not result:
            # Create password with salt
            salt = secrets.token_hex(16)
            password_hash = hash_password("admin123", salt)
            
            cursor.execute("""
                INSERT INTO users (email, caterer_id, password, password_salt, name, role, status, specialties)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                'admin@catercloud.com',      # email
                999999,                           # caterer_id (integer)
                password_hash,               # password (hashed)
                salt,                        # password_salt
                'Admin User',                # name
                'admin',                     # role
                'active',                    # status
                Json([])                     # specialties (empty list as JSON)
            ))

            conn.commit()

def hash_password(password, salt):
    """Hash password with salt using SHA-256"""
    return hashlib.sha256((password + salt).encode()).hexdigest()
# Authentication functions
def login(email, password):
    """Authenticate user login - use DuckDB for faster authentication"""
   
    with get_pg_connection() as conn:
         with conn.cursor() as cursor: 
            cursor.execute("SELECT * FROM users WHERE email = %s", [email])
            result = cursor.fetchone()
            print(f"Fetched result: {result}")  # Fetch one result
            if result:
                columns = [desc[0] for desc in cursor.description]
                user = result
                print(f"User data: {user}")  # Debugging line
                password_hash = hash_password(password, user['password_salt'])
                print(f"Password Hash: {password_hash}")
                print (f"Password Salt:{user['password_salt']}")  # Debugging line
               
                if user["password"] == password_hash:
                    st.session_state.authenticated = True
                    st.session_state.current_user = email
                    st.session_state.current_role = user["role"]
                    st.session_state.current_user_name = user["name"]
                    st.session_state.current_caterer_id = user["caterer_id"]
                    st.session_state.current_caterer_address = user["address"]
                else:
                    return False

                # Set initial page based on role
                if user["role"] == "admin":
                    st.session_state.page = "admin_dashboard"
                else:
                    st.session_state.page = "caterer_dashboard"
            else :   
                return False
    
    return True


def logout():
    """Log out the current user and reset state"""
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.session_state.current_role = None
    st.session_state.page = "login"

# Navigation functions
def navigate_to(page_name):
    """Change current page"""
    st.session_state.page = page_name
    st.rerun()

# UI Components - Login
def display_login_page():
    """Display the login page UI"""
    st.markdown(f"<h1 class='main-header'>Welcome to {APP_NAME}</h1>", unsafe_allow_html=True)
    st.markdown("<h2 class='sub-header'>Login to your account</h2>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            submit = st.form_submit_button("Login")
        
        with col2:
            if submit:
                if login(email, password):
                    st.success("Login successful!")
                    st.rerun()  # Rerun to show the dashboard
                else:
                    st.error("Invalid email or password")

# Admin UI Components
def display_admin_sidebar():
    """Display sidebar navigation for admin"""
    st.sidebar.title("Admin Dashboard")
    st.sidebar.write(f"Welcome, {st.session_state.current_user_name}")
    
    # Admin navigation options
    admin_pages = {
        "admin_dashboard": "Dashboard",
        "manage_caterers": "Manage Caterers",
        "manage_orders": "View All Orders", 
        "admin_settings": "Settings"
    }
    
    # Navigation buttons
    for page_id, page_name in admin_pages.items():
        if st.sidebar.button(page_name, key=f"nav_{page_id}"):
            navigate_to(page_id)
    
    # Logout button at the bottom
    st.sidebar.divider()
    if st.sidebar.button("Logout", key="admin_logout"):
        logout()
        st.rerun()

def display_admin_dashboard():
    """Display the admin dashboard main page"""
    st.title("Admin Dashboard")
    
    # Show basic stats
    caterers = get_all_caterers()
    if not caterers:    
        st.warning("No caterers found.")
         
    else :
        active_caterers = sum(1 for c in caterers if c["role"] == "caterer" and c["status"] == "active")
        pending_caterers = sum(1 for c in caterers if c["role"] == "caterer" and c["status"] == "pending")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Caterers", len(caterers) - 1)  # Subtract admin
        col2.metric("Active Caterers", active_caterers)
        col3.metric("Pending Approvals", pending_caterers)
        
    st.subheader("Quick Actions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Manage Caterers"):
            navigate_to("manage_caterers")
    with col2:
        if st.button("View Orders"):
            navigate_to("manage_orders")

def display_manage_caterers():
    """Display the caterer management page for admin"""
    st.title("Manage Caterers")
     # Add button to create new caterer
    if st.button("➕ Add New Caterer"):
        st.session_state.page = "add_new_caterer"
        st.rerun()
    caterers = get_all_caterers()
    if not caterers:
        st.warning("No caterers found.")
        return
        
   # caterer_list = [(c["email"], c) for c in caterers if c.get("role") == "caterer"]
    
    # Tabs for active and pending caterers
    tab1, tab2 ,tab3 = st.tabs(["Active Caterers", "InActive Caterers" ,"Pending Approvals"])
    
    with tab1:
        active_caterers = [c for c in caterers if c.get("status") == "active"]
        if not active_caterers:
            st.info("No active caterers.")
        else:
            for caterer in active_caterers:
                email = caterer.get("email", "No email")
                with st.expander(f"{caterer['name']} ({email})"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**Name:** {caterer['name']}")
                        st.write(f"**Contact:** {caterer.get('phone', 'Not provided')}")
                        st.write(f"**Address:** {caterer.get('address', 'Not provided')}")
                        specialties = caterer.get('specialties', [])
                        if specialties:
                            st.write(f"**Specialties:** {', '.join(specialties)}")
                    
                    with col2:
                    # Deactivate caterer option
                        if st.button("Deactivate", key=f"deactivate_{email}"):
                            # Find the caterer in the original list and update
                            for c in caterers:
                                if c.get("email") == email:
                                    update_caterer_status(email, "inactive")     
                                    break
                            st.success(f"Caterer {caterer['name']} has been deactivated.")
                            st.rerun()

    with tab2:
        # Filter for inactive caterers
        inactive_caterers = [c for c in caterers if c.get("status") == "inactive"]
        if not inactive_caterers:
            st.info("No inactive caterers.")
        else:
            for caterer in inactive_caterers:
                email = caterer.get("email", "No email")
                with st.expander(f"{caterer['name']} ({email})"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**Name:** {caterer['name']}")
                        st.write(f"**Contact:** {caterer.get('phone', 'Not provided')}")
                        st.write(f"**Address:** {caterer.get('address', 'Not provided')}")
                        specialties = caterer.get('specialties', [])
                        if specialties:
                            st.write(f"**Specialties:** {', '.join(specialties)}")
                    
                    with col2:
                        # Reactivate caterer option
                        if st.button("Activate", key=f"activate_{email}"):
                            for c in caterers:
                                if c.get("email") == email:
                                    update_caterer_status(email, "active")  
                                    break
                            st.success(f"Caterer {caterer['name']} has been activated.")
                            st.rerun()
    with tab3:
        pending_caterers = [c for c in caterers if c.get("status") == "pending"]
        if not pending_caterers:
            st.info("No pending approval requests.")
        else:
            pending_caterers = [c for c in caterers if c.get("status") == "pending"]
            for caterer in pending_caterers:
                email = caterer.get("email", "No email")
                with st.expander(f"{caterer['name']} ({email})"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**Name:** {caterer['name']}")
                        st.write(f"**Contact:** {caterer.get('phone', 'Not provided')}")
                        st.write(f"**Address:** {caterer.get('address', 'Not provided')}")
                        specialties = caterer.get('specialties', [])
                        if specialties:
                            st.write(f"**Specialties:** {', '.join(specialties)}")
                    
                    with col2:
                        # Approve caterer option
                        if st.button("Approve", key=f"approve_{email}"):
                            for c in caterers:
                                if c.get("email") == email:
                                    update_caterer_status(email, "active")            
                                    break
                            st.success(f"Caterer {caterer['name']} has been approved.")
                            st.rerun()
                        
                        # Reject caterer option
                        if st.button("Reject", key=f"reject_{email}"):
                            for c in caterers:
                                if c.get("email") == email:
                                    c["status"] = "rejected"
                                    break
                            st.success(f"Caterer {caterer['name']} has been rejected.")
                            st.rerun()

def display_admin_settings():
    """Display the admin settings page"""
    st.title("Admin Settings")
    st.write("Configure application settings here.")
    
    # Sample settings form
    with st.form("admin_settings_form"):
        app_name = st.text_input("Application Name", value=APP_NAME)
        enable_registration = st.checkbox("Allow New Caterer Registration", value=True)
        
        submit = st.form_submit_button("Save Settings")
        if submit:
            # Here you would save these settings to a config file
            st.success("Settings saved successfully!")


# Caterer UI Components
def display_caterer_sidebar():
    """Display sidebar navigation for caterers"""
    caterer_data = get_caterer_by_caterer_id(st.session_state.current_caterer_id)
    header_left, header_right = st.columns([4, 1])
    with header_right:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.page == "caterer_dashboard"
            st.query_params["page"] = "caterer_dashboard"
            st.rerun()
    st.markdown(f"""
    <div class="custom-header">
        <h1>Welcome, {caterer_data['name']}</h1>
    </div>
    """, unsafe_allow_html=True)
  

    img_base64 = get_base64_image("images/icon.jpeg")
    with st.sidebar:
        st.markdown(f"""
        <img src="data:image/png;base64,{img_base64}"  
                    class="sidebar-logo" 
                    alt="Logo">
                    """, unsafe_allow_html=True)
        st.divider() 
       
    
    # Status indicator
    status_color = "green" if caterer_data["status"] == "active" else "red"
    st.sidebar.markdown(f"Status: <span style='color:{status_color};font-weight:bold'>{caterer_data['status'].upper()}</span>", unsafe_allow_html=True)
    
    # Caterer navigation options
    caterer_pages = {
        "caterer_dashboard": "📊 Dashboard",
        "caterer_menu": " 📋 Menu Management",
        "caterer_orders": "🍽️ Orders",
        "caterer_profile": "👥My Profile",
        
    }
    
    # Navigation buttons
    for page_id, page_name in caterer_pages.items():
        if st.sidebar.button(page_name, key=f"nav_{page_name}"):
            st.query_params["page"] = page_id
            st.session_state.page=page_id
            st.rerun()
    
    # Logout button at the bottom
    st.sidebar.divider()
    if st.sidebar.button("Logout", key="caterer_logout"):
        logout()
        st.rerun()


def display_add_caterer():
    """Display form to add a new caterer by admin"""
    st.title("Add New Caterer")
    
    # Back button
    if st.button("← Back to Caterer Management"):
        st.session_state.page = "manage_caterers"
        st.rerun()
    
    # Caterer creation form
    with st.form("add_caterer_form"):
        email = st.text_input("Email Address*")
        password = st.text_input("Password*", type="password")
        name = st.text_input("Kitchen/Business Name*")
        phone = st.text_input("Contact Number")
        address = st.text_area("Kitchen Address")
        
        # Multiple selection for food specialties
        specialties_options = [
            "North Indian", "South Indian", "Chinese", "Continental", 
            "Italian", "Mexican", "Street Food", "Desserts", "Healthy",
            "Vegetarian", "Non-Vegetarian"
        ]
        specialties = st.multiselect("Select Specialties", options=specialties_options)
        
        # Admin-only options
        status = st.selectbox("Status", ["active", "pending", "inactive"], index=0)
        
        submit = st.form_submit_button("Create Caterer")
    if submit:
        if not email or not password or not name:
            st.error("Email, password and kitchen name are required!")
        else : 
            result = register_caterer(email, password, name, phone, address, specialties, "")
            # Immediately set status as selected by admin
            if result["success"]:
                # Immediately set status as selected by admin
                #update_caterer_profile(email, status)
                st.success(f"Caterer '{name}' created successfully!")
                
                # Return to caterer management after short delay
                time.sleep(1)
                st.session_state.page = "manage_caterers"
                st.rerun()
            else :
             st.error(result["error"])

def register_caterer(email, password, name, phone, address, specialties, bio=""):
    """Register a new caterer with improved validation and error handling"""
    # Input validation
    if not email or not password or not name:
        return {"success": False, "error": "Required fields missing"}
        
    # Email format validation
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return {"success": False, "error": "Invalid email format"}
    
    # Password strength check
    if len(password) < 6:
        return {"success": False, "error": "Password too short (minimum 6 characters)"}
    
    # Check if user already exists in PostgreSQL
    with get_pg_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()
        if result:
            return {"success": False, "error": "Email already exists"}
    
        try:
            # Create password with salt
            salt = secrets.token_hex(16)
            password_hash = hash_password(password, salt)
            
            # Set default bio if empty
            if not bio or bio.strip() == "":

                bio = f"Welcome to {name}'s kitchen!"
            print(f"Bio: {bio}")
            # Get the next caterer_id (find max and increment)
            cursor.execute("SELECT MAX(caterer_id) FROM users WHERE role ='caterer'")
            max_id_result = cursor.fetchone()
            print("max_id_result:", max_id_result)
            print("type:", type(max_id_result))
            print(f"Cursor rowcount: {cursor.rowcount}")
            next_caterer_id = 1  # default fallback
            if max_id_result and max_id_result['max'] is not None:
                next_caterer_id = max_id_result[max] + 1
            
            print(f"Next caterer_id: {next_caterer_id}")

            # Create the caterer with the next caterer_id
            cursor.execute("""
                    INSERT INTO users (
                        email, caterer_id, password, password_salt, name, role, status, 
                        phone, address, specialties, bio, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    email,
                    next_caterer_id,
                    password_hash,
                    salt,
                    name,
                    'caterer',
                    'pending',
                    phone,
                    address,
                    Json(specialties),  # assumes you're using psycopg2.extras.Json
                    bio,
                    datetime.now()
                ))

            conn.commit()
            # Return the caterer_id in the response
        except Exception as e:
        # Log the error
            print(f"Error registering caterer: {e}")
            print(f"Type: {type(e).__name__}")
            print(f"Message: {e}")
            return {"success": False, "error": "Database error"}
    
    return {"success": True}

def display_caterer_orders():
    """Display orders page for caterer"""
    st.subheader("Manage Orders")
    # Load orders from database
    col1,col3 = st.columns([1, 4])
    with col1:
        order_sel_input = st.date_input(
                            "Select Date",
                            value= datetime.today(),
                            format="DD/MM/YYYY",
                    )
    
    orders = load_order_items(st.session_state.current_caterer_id,order_sel_input, status=None)
    print  (f"Orders: {orders}")  # Debugging line
    # Filter tabs
    tabs = st.tabs(["All Orders", "Accepted" ,"Pending", "Ready", "Completed", "Cancelled","Rejected"])
    
    with tabs[0]:
        orders = load_order_items(st.session_state.current_caterer_id,order_sel_input)
        display_orders(orders)

    with tabs[1]:
        orders = load_order_items(st.session_state.current_caterer_id, order_sel_input, "accepted")
        display_orders(orders, tab_name=tabs[1])

    with tabs[2]:
        orders = load_order_items(st.session_state.current_caterer_id, order_sel_input, "pending")
        display_orders(orders,tabs[2])

    with tabs[3]:
        orders = load_order_items(st.session_state.current_caterer_id,order_sel_input, "ready")
        display_orders(orders,tabs[3])

    with tabs[4]:
        orders = load_order_items(st.session_state.current_caterer_id,order_sel_input, "completed")
        display_orders(orders,tabs[4])

    with tabs[5]:
        orders = load_order_items(st.session_state.current_caterer_id, order_sel_input ,"cancelled")
        display_orders(orders,tabs[5])

    with tabs[6]:
        orders = load_order_items(st.session_state.current_caterer_id,order_sel_input, "rejected")
        display_orders(orders,tabs[6])


def display_orders(orders,tab_name="All Orders"):
    """Display orders management page"""
    if not orders:
        st.info(f"No orders found.")
        return
    for order in orders:
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                col1.write(f"**{order['order_id']} - {order['customer_name']}**")
                col1.write(f"{order['items']}")
                col1.write(f"Special Instructions : {order['special_instructions']}")
                col1.write(f"Payment Status:{order['payment_status']}")
                col1.write(f"Payment Method :{order['payment_method']}")
                col2.write(f"**Total:** ₹{order['total']}")
                col2.write(f"**Status:** {order['status']}")
                
                # Action buttons based on status
                if order["status"] == "pending":
                    col3_left, col3_right = col3.columns(2)
                    if col3_left.button("Accept", key=f"{tab_name}_accept_{order['order_id']}"):
                        # Update order status in database
                        update_order_status(order['order_id'], "accepted")
                        st.success(f"Order {order['order_id']} Accepted!")
                    if col3_right.button("Reject", key=f"{tab_name}_reject_{order['order_id']}"):
                        update_order_status(order['order_id'], "rejected")
                        st.success(f"Order {order['order_id']} Rejected!")
                elif order["status"] == "accepted":
                    col3_left, col3_right = col3.columns(2)
                    if col3_left.button("Mark Ready", key=f"{tab_name}_ready_{order['order_id']}"):
                        update_order_status(order['order_id'], "ready")
                        st.success(f"Order {order['order_id']} Mark as ready!")
                    if col3_right.button("Cancel", key=f"{tab_name}_cancel_accepted_{order['order_id']}"):
                        update_order_status(order['order_id'], "cancelled")
                        st.success(f"Order {order['order_id']} Cancelled!")
                elif order["status"] == "ready":
                    col3_left, col3_right = col3.columns(2)
                    if col3_left.button("Complete", key=f"{tab_name}_complete_{order['order_id']}"):
                        update_order_status(order['order_id'], "completed")
                        st.success(f"Order {order['order_id']} completed!")
                    if col3_right.button("Cancel", key=f"{tab_name}_cancel_ready_{order['order_id']}"):
                        update_order_status(order['order_id'], "cancelled")
                        st.success(f"Order {order['order_id']} Cancelled!")
                elif order["status"] == "cancelled":
                    col3.write("Order Cancelled - No action required")
                elif order["status"] == "completed":
                    col3.write("Order Completed - No action required")
                elif order["status"] == "rejected":
                    col3.write("Order Rejected - No action required")
                st.divider()
        
def display_caterer_menu(): 
    """Display menu management for caterer"""
    # st.title("Menus Published ")
  # Sidebar for caterer selection
    #st.sidebar.header("Settings")
    #caterer_id = st.sidebar.number_input("Caterer ID", min_value=1, value=1)
    caterer_id= st.session_state.current_caterer_id
    # Load all menus for the selected caterer
    all_menus = load_caterer_menus(caterer_id)
    
    if not all_menus:
        st.info(f"No menus found . Please upload a menu.")
        return
    
    # Create a DataFrame for all menus
    menus_data = []
    for menu in all_menus:
        formatted_date = format_date(menu['menu_date'])
        extracted_date = extract_date_from_menu_id(menu['menu_id'])
        
        menus_data.append({
            "Menu ID": menu['menu_id'],
            "Date": formatted_date,
            "Extracted Date": extracted_date,
            "Name": menu['name'],
            "Order Link": menu['orderlink'],
            "Active": "Yes" if menu['active'] else "No",
            "Created At": menu['created_at']
        })
    
    menus_df = pd.DataFrame(menus_data)
    
    for index, row in menus_df.iterrows():
        menu_id = row['Menu ID']
        date = row['Date']
        extracted_date=row['Extracted Date']
        edit_key = f"can_edit_menu_{menu_id}"
        if edit_key not in st.session_state:
            st.session_state[edit_key] = False
        # Create an expander for each menu
        with st.expander(f"{menu_id} | {date}"):
            # Load detailed information when expander is clicked
            menu_details = load_menu_details(menu_id)
            ordercount= checkif_order_exists_for_menu(menu_id)
            print(f"Order Count for this menu {ordercount}")
            st.session_state[edit_key] = (ordercount == 0)
            print(st.session_state[edit_key])
            if menu_details:
                # Display menu information
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Menu Information")
                    st.write(f"**Name:** {menu_details['name']}")
                    st.write(f"**Date:** {format_date(menu_details['menu_date'])}")
                    st.write(f"**Status:** {'Active' if menu_details['active'] else 'Inactive'}")
                    st.write(f"**Order Link :** { menu_details['orderlink'] if menu_details['active'] else 'Menu is not active'}")
                    # Add the orders section
                    show_orders = st.checkbox("Show Orders", key=f"show_orders_{menu_id}_{index}")
        
                with col2:
                    
                    st.subheader("Menu Items")
                    if menu_details['items']:
                        # Create a DataFrame for the menu items
                        items_df = pd.DataFrame(menu_details['items'])
                        
                        # Rename columns for better display
                        if 'item_name' in items_df.columns:
                            items_df = items_df.rename(columns={'item_name': 'Item'})
                        if 'price' in items_df.columns:
                            items_df = items_df.rename(columns={'price': 'Price'})
                            items_df['Price'] = items_df['Price']
                        
                        # Display either the regular dataframe or editable version
                    menu_summary_df = pd.DataFrame(items_df)[['Item', 'Price']]
    
                    if  st.session_state[edit_key] :
                        edited_items_df = st.data_editor(
                                menu_summary_df,
                                num_rows="dynamic",  # Allows adding new rows
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "Item": st.column_config.TextColumn("Menu Item", required=True),
                                    "Price": st.column_config.NumberColumn(
                                                f"Price ({RESTAURANT_CONFIG['currency']})", 
                                                min_value=0, 
                                                format=f"{RESTAURANT_CONFIG['currency']}%.2f",
                                                required=True
                                    )
                                },
                                key =f"edited_df_{menu_id}"
                            )
                        
                        if st.button(f"Save Menu", key=f"edit_btn_{menu_id}"):
                            success=update_menu_items_db(edited_items_df,extracted_date)
                            if success:
                                st.info("Menu Items Updated Successfully")
                    else:
                        st.dataframe(menu_summary_df, hide_index=True)
                if show_orders:
                    display_orders_for_selected_menu(menu_id, index)
           
            else:
                st.error(f"Could not load details for menu {menu_id}")
                                 
def display_caterer_profile():
    """Display profile management for caterer"""
     
    caterer_data = get_caterer_by_caterer_id(st.session_state.current_caterer_id)
    
    st.subheader("My Profile")
    
    # Edit profile form
    with st.form("edit_profile_form"):
        name = st.text_input("Kitchen Name", value=caterer_data["name"])
        phone = st.text_input("Phone Number", 
                              value=caterer_data.get("phone", ""),
                              disabled=True,
                              help="Please contact administrator for changes to phone number" )
        address = st.text_area("Address", value=caterer_data.get("address", ""))
        
        specialties_options = [
            "North Indian", "South Indian", "Chinese", "Continental", 
            "Italian", "Mexican", "Street Food", "Desserts"
        ]
        specialties = st.multiselect(
            "Specialties", 
            options=specialties_options,
            default=caterer_data.get("specialties", [])
        )
        
        # Password change section
        st.subheader("Change Password")
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        submit = st.form_submit_button("Update Profile")
        
        if submit:
            # Here you would validate and save the profile changes
            # For password change, add validation in real app
            if new_password and new_password == confirm_password:
                # Create password with salt
                 salt = secrets.token_hex(16)
                 password_hash = hash_password(new_password, salt)
            elif new_password is None and confirm_password is None:
                 print("Password change is not required")
            else :
                st.caption("ℹ️ Password and Confirm Password should match")

            set_clause = ""
            params = []
            if name is not None and name.strip():
                if set_clause:
                    set_clause += ", "
                set_clause += "name = %s"
                params.append(name)
            # Handle address update
            if address is not None and address.strip():
                if set_clause:
                    set_clause += ", "
                set_clause += "address = %s"
                params.append(address)
            # Handle specialties update (as JSONB)
            if specialties is not None:
                # Convert to JSON string if it's a list or dict
                if isinstance(specialties, (list, dict)):
                    specialties_json = json.dumps(specialties)
                else:
                    specialties_json = specialties
                
                if set_clause:
                    set_clause += ", "
                set_clause += "specialties = %s::jsonb"
                params.append(specialties_json)
            if new_password is not None and new_password.strip():
                if set_clause:
                    set_clause += ", "
                    set_clause += "password = %s, password_salt = %s"
                    params.append(password_hash)
                    params.append(salt)
            query = f"""
            UPDATE users
            SET {set_clause}
            WHERE caterer_id = %s
            RETURNING *
            """
            params.append(st.session_state.current_caterer_id)

            with get_pg_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)

            updated_user = cursor.fetchone()
            if updated_user:
                conn.commit()
                st.success("Profile updated successfully!")
                return
            

def display_caterer_uploadmenu():
    """Upload Menu for caterer"""
    # Read query parameters
    params = st.query_params
    menu_id = params["menu_id"] if "menu_id" in params else None
    caterer_id= st.session_state.current_caterer_id

    st.title(f"{RESTAURANT_CONFIG['emoji']} {RESTAURANT_CONFIG['name']}")
    # --- ADMIN MODE ---
    if menu_id is None:
        st.header("👩‍💼 Upload Menu Here To Generate Order Form")

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

               
                date_str=date_converter(extracted_date)
        
                # Use it in the date picker
                extracted_date_obj = datetime.strptime(date_str, "%d%m%Y").date()
                menu_date_input = st.date_input(
                        "Menu Date",
                        value=extracted_date_obj,
                        format="DD/MM/YYYY",
                )
                # Convert the date to the desired format
                #formatted_date = menu_date_input.strftime("%d%m%Y")
                if st.button("Save Menu & Generate Link"):

                    # Create menu ID with date and timestamp
                    menu_id = f"M{menu_date_input.strftime("%d%m%Y")}"
                    try:

                        
                        #base_url = "http://localhost:8509"  # Change this to your deployed URL 
                        #base_url = "https://mycloudkitchen.streamlit.app/" # deployed URL
                        order_link = f"{ADMIN_CONFIG['base_url']}?menu_id={menu_id}"

                        #sheet_url = save_menu_to_sheets(edited_df, menu_id,order_link,extracted_date_obj)
                        menu_url =save_menu_db(edited_df, menu_id,order_link,menu_date_input,caterer_id)

                        st.success("✅ Order Form Link Generated! Share this with Customer for placing their orders.")
                        st.markdown(f"[🔗 Click Here to View Order Form]({order_link})")
                        #st.code(order_link)
                        st.success("Menu saved successfully!")
                    except Exception as e:
                        st.error(f"Error saving to Google Sheets: {str(e)}")
                        st.info("Make sure you've set up the Google Sheets API credentials correctly.")



def display_caterer_add_new_menu():
    """Section for adding a new menu"""
    st.header("Add New Menu")
    
    # Create tabs for manual entry vs file upload
    add_method = st.radio(
        "Choose how to add menu",
        options=["Manual Entry", "Upload File"],
        horizontal=True
    )

    if add_method == "Manual Entry":
        display_add_new_menu_manual()
    else:
        display_caterer_uploadmenu()
    return

def display_add_new_menu_manual():
    """ Upload new Menu Manually """
    st.markdown("Manual Menu Entry")
        # Menu items section using dataframe editor with column configuration
    
    
    # Function to generate unique keys
    def get_unique_key():
        return str(uuid.uuid4())
    
    # Function to clear the data editor
    def clear_data_editor():
        # Replace the source DataFrame with an empty one
        st.session_state.menu_items_df = pd.DataFrame(columns=["Item", "Price"])
        # Generate a new unique key for the editor
        st.session_state.editor_key = get_unique_key()
        # Set a flag to show success message
        st.session_state.just_cleared = True
        # Force a rerun to update the UI
        st.rerun()

    
    col1, col2, col3 = st.columns(3)
    with col1:
        #st.subheader("Add Menu ") 
        menu_date = st.date_input("Select the Menu Date", value=datetime.now().date())

    st.markdown(f"Add items to your menu with prices in {RESTAURANT_CONFIG['currency']}")
    # Initialize session state for menu dataframe if it doesn't exist
    if 'menu_items_df' not in st.session_state:
    # Create empty DataFrame with explicit data types
        st.session_state.menu_items_df = pd.DataFrame({
            "Item": pd.Series(dtype='str'),
            "Price": pd.Series(dtype='float64')
    })
        
    # Create a key for the editor to track changes
    if 'editor_key' not in st.session_state:
        st.session_state.editor_key = get_unique_key()
    
    
    # Configure the columns for the data editor
    column_config = {
        "Item": st.column_config.TextColumn("Item", required=True),
        "Price": st.column_config.NumberColumn(
            f"Price ({RESTAURANT_CONFIG['currency']})", 
            min_value=0, 
            format=f"{RESTAURANT_CONFIG['currency']}%.2f",
            required=True
        ),
        "_index": None
    }

    with st.form("data_form"):
    # Display the current data in an editor
   
    # Create the data editor
        edited_df = st.data_editor(
            st.session_state.menu_items_df,
            column_config=column_config,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key=st.session_state.editor_key,
            #on_change=update_dataframe
        )
  
        menu_url=""    # Add a submit button
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.form_submit_button("Save", type="primary", use_container_width=True):
            # Create menu ID with date and timestamp
                menu_id = f"M{menu_date.strftime("%d%m%Y")}"
                try:

                    base_url = "http://localhost:8509"  # Change this to your deployed URL 
                    #base_url = "https://mycloudkitchen.streamlit.app/" # deployed URL
                    order_link = f"{base_url}?menu_id={menu_id}"

                    #sheet_url = save_menu_to_sheets(edited_df, menu_id,order_link,extracted_date_obj)
                    menu_url =save_menu_db(edited_df, menu_id,order_link,menu_date,st.session_state.current_caterer_id)

                except Exception as e:
                    # Log the error
                    print(f"Message: {e}")

        with col2:
            if st.form_submit_button("Clear", use_container_width=True):
                st.session_state.menu_items_df = pd.DataFrame(columns=["Item", "Price"])
                st.dataframe(st.session_state.menu_items_df, hide_index=True,key=st.session_state.editor_key)
                clear_data_editor()
                #st.session_state.menu_items_df = pd.DataFrame({"Item": [], "Price": []})
        with col3:
            if st.form_submit_button("Cancel", use_container_width=True):
                navigate_to("caterer_menu")

        if menu_url:
            
            st.success("✅ Order Form Link Generated! Share this with Customer for placing their orders.")
            st.markdown(f"[🔗 Click Here to View Order Form]({order_link})")    
            #st.code(order_link)
            st.success("Menu saved successfully!")

    return 

def display_menu():
    """ This is Menu Management Screen - Add Menu(Manual or Upload), View Existing Menus """
    st.subheader("Menu Management") 

    # Create columns to position buttons
    addmenu, colspace , addmenucatalog = st.columns([1, 1 ,1])
    with addmenu: # Adjust ratios as needed
        if st.button("Add new menu ",key="add_new_menu"):
            st.query_params["page"] = "add_new_menu"
            st.session_state.page = "add_new_menu"
            st.rerun()
    with addmenucatalog:
        if st.button(" 📋 Maintain Menu catalog", key="add_menu_catalog"):
            st.query_params["page"] = "menu_catalog"
            st.session_state.page = "menu_catalog"
            st.rerun()
    

    # Main header with add button
    col1, col2 = st.columns([5, 1])
    with col1:
            display_caterer_menu()
    
    
    return

# Integrate this into your existing menu expander code
def display_orders_for_selected_menu(menu_id, menu_index):
    """Display all orders for the selected menu without using nested expanders"""
    st.header("Orders for this Menu")
    # Load orders for this menu
    orders = load_orders_by_menu(menu_id)
    
    if not orders:
        st.info(f"No orders found for menu: {menu_id}")
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
    for order in orders:
        # Calculate number of items and quantity
        num_items = len(order['items']) if isinstance(order['items'], dict) else 0
        total_quantity = sum([item.get('quantity', 0) for item in order['items'].values()]) if isinstance(order['items'], dict) else 0
        
        order_summaries.append({
            "Order ID": order['order_id'],
            "Customer": order['customer_name'],
            "Date": format_datetime(order['order_date']),
            "Total": f"£{order['total']:.2f}",
            "Status": order['status'].capitalize(),
            "Items": num_items,
            "Quantity": total_quantity
        })
    
    # Display the item summary for this menu
    st.subheader("Menu Item Summary")
    if summary_items:
        # Format the price with pound symbol
        for item in summary_items:
            item["Price"] = f"£{item['Price']:.2f}"
            
        menu_summary_df = pd.DataFrame(summary_items)
        st.dataframe(menu_summary_df, key=f"menu_summary_df_{menu_id}_{menu_index}",hide_index=True)
    else:
        st.info("No items ordered from this menu")
    
    # Display order summary
    st.subheader("Order Summary")
    summary_df = pd.DataFrame(order_summaries)
    st.dataframe(summary_df, key=f"summary_df_{menu_id}_{menu_index}")
    
    # Display detailed view of each order using tabs instead of expanders
    st.subheader("Order Details")
    
    # Create tabs for each order instead of using expanders
    if len(orders) > 0:
        tab_labels = [f"Order: {order['order_id']} - {order['customer_name']}" for order in orders]
        tabs = st.tabs(tab_labels)
        
        for i, (tab, order) in enumerate(zip(tabs, orders)):
            with tab:
                order_id = order['order_id']
                col1, col2 = st.columns(2)
                #Convert Customer Address from JSON Format to Display format
                if order['customer_address'].get('address_line1') !='Pickup' :
                    formatted_address = f"{order['customer_address'].get('address_line1', '')}"
                    if order['customer_address'].get('address_line2'):
                        formatted_address += f", {order['customer_address'].get('address_line2')}"
                    formatted_address += f", {order['customer_address'].get('city', '')}, {order['customer_address'].get('postcode', '')}"
                else :
                    formatted_address='Pickup'
                with col1:
                    st.subheader("Customer Information")
                    st.write(f"**Name:** {order['customer_name']}")
                    st.write(f"**Phone:** {order['customer_phone']}")
                    st.write(f"**Address:** { formatted_address or 'Pickup'}")
                    
                    st.subheader("Order Information")
                    st.write(f"**Order Date:** {format_datetime(order['order_date'])}")
                    st.write(f"**Delivery Date:** {format_date(order['delivery_date']) if order['delivery_date'] else 'N/A'}")
                    st.write(f"**Payment Method:** {order['payment_method'] or 'N/A'}")
                    st.write(f"**Status:** {order['status'].capitalize()}")
                    st.write(f"**Total:** £{order['total']:.2f}")
                    
                    if order['special_instructions']:
                        st.subheader("Special Instructions")
                        st.write(order['special_instructions'])
                
                with col2:
                    st.subheader("Items Ordered")
                    
                    if isinstance(order['items'], dict) and order['items']:
                        # Convert items dictionary to DataFrame with the requested format
                        items_data = []
                        for item_name, details in order['items'].items():
                            items_data.append({
                                "Item Name": item_name,
                                "Total Items Ordered": details['quantity'],
                                "Price": f"£{details['price']:.2f}"
                            })
                        
                        items_df = pd.DataFrame(items_data)
                        st.dataframe(items_df, key=f"items_{menu_id}_{order_id}_{i}",hide_index=True)
                    else:
                        st.info("No items found for this order")


