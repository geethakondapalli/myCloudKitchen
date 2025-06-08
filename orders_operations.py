import psycopg2
import os
from datetime import datetime
from db_operations import get_pg_connection, generate_order_id  
from restaurant_config import RESTAURANT_CONFIG
import json
import streamlit as st
from utils import extract_date_from_menu_id, format_date

# Function to load orders for a specific menu

def checkif_order_exists_for_menu(menu_id):

    """Check if orders placed for a specific menu"""
    conn = None
    cursor = None
    try:
        conn = get_pg_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Query to get all orders for the specified menu
        query = """
        SELECT count(*)
        FROM orders
        WHERE menu_id = %s
        """
        cursor.execute(query, (menu_id,))
        results = cursor.fetchone()
        print(f"Count : {results['count']}")
        print(results)
        return results['count']
    except Exception as e:
        st.error(f"Error loading orders: {e}")
        return []

    return
def load_orders_by_menu(menu_id):
    """Load all orders placed for a specific menu"""
    conn = None
    cursor = None
    try:
        conn = get_pg_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Query to get all orders for the specified menu
        query = """
        SELECT order_id, customer_name, customer_phone, customer_address, 
               order_date, delivery_date, items, total, payment_method, 
               status, special_instructions
        FROM orders
        WHERE menu_id = %s and status not in ('pending','cancelled','rejected')
        ORDER BY order_date DESC
        """
        cursor.execute(query, (menu_id,))
        results = cursor.fetchall()
        
        orders = []
        for row in results:
            # Convert items from JSONB to Python dict
            items_data = row['items']
            customer_address = row['customer_address']
            
            order = {
                "order_id": row['order_id'],
                "customer_name": row['customer_name'],
                "customer_phone": row['customer_phone'],
                "customer_address": customer_address,
                "order_date": row['order_date'],
                "delivery_date": row['delivery_date'],
                "items": items_data,
                "total": row['total'],
                "payment_method": row['payment_method'],
                "status": row['status'],
                "special_instructions": row['special_instructions']
            }
            orders.append(order)
        
        return orders
        
    except Exception as e:
        st.error(f"Error loading orders: {e}")
        return []
    
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
                
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

def checkif_order_exists_for_selected_date(selected_date):

    """Check if orders placed for a specific menu"""
    conn = None
    cursor = None
    try:
        conn = get_pg_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Query to get all orders for the specified menu
        query = """
        SELECT count(*)
        FROM orders
        WHERE menu_date = %s
        """
        cursor.execute(query, (selected_date,))
        results = cursor.fetchone()
        print(f"Count : {results['count']}")
        print(results)
        return results['count']
    except Exception as e:
        st.error(f"Error loading orders: {e}")
        return []
    
def get_all_orders():
    """Get all orders """
    
    with get_pg_connection() as conn:
        with conn.cursor() as cursor:
            # Fetch all orders
            result = conn.execute("SELECT * FROM orders ORDER BY order_date DESC").fetchall()
            if(result is None):
                return []
            orders = result
        # Convert items from JSON string to list
        for order in orders:
            order["items"] = json.loads(order["items"])
        
    return orders

def acknowledge_orders(todays_date):
    
    """Orders to be acknowledge for the day"""
    conn = None
    cursor = None
    try:
        conn = get_pg_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Query to get all orders for the specified menu
        query = """
            SELECT order_id, customer_name, customer_phone, customer_address, 
                order_date, delivery_date, items, total, payment_method, 
                status, special_instructions
            FROM orders
            WHERE menu_date = %s
            AND status= %s
            ORDER BY order_date DESC
        """
        cursor.execute(query, (todays_date,'pending'))
        results = cursor.fetchall()
        
        orders = []
        for row in results:
            # Convert items from JSONB to Python dict
            items_data = row['items']
            
            order = {
                "order_id": row['order_id'],
                "customer_name": row['customer_name'],
                "customer_phone": row['customer_phone'],
                "customer_address": row['customer_address'],
                "order_date": row['order_date'],
                "delivery_date": row['delivery_date'],
                "items": items_data,
                "total": row['total'],
                "payment_method": row['payment_method'],
                "status": row['status'],
                "special_instructions": row['special_instructions']
            }
            orders.append(order)

        return orders
       
    except Exception as e:
        st.error(f"Error loading orders: {e}")
        return []
    
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
                
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass 
    return


def get_delivery_address_list(todays_date):
    
    try:
        with get_pg_connection() as conn:
            with conn.cursor() as cursor:
                # Fetch all unique delivery addresses
                # Query to get all orders for the specified menu
                query = """
                SELECT order_id, customer_name, customer_phone, customer_address
                FROM orders
                WHERE menu_date = %s
                AND customer_address->>'address_line1' != %s 
                AND status not in ('pending','cancelled','rejected')
                ORDER BY order_id ASC
                """
                cursor.execute(query, (todays_date,'Picking up from restuarant'))
                results = cursor.fetchall()
                delivery_addresses = []
            for row in results:
                full_address = f"{row['customer_address'].get('address_line1', '')}"
                if row['customer_address'].get('address_line2'):
                    full_address += f", {row['customer_address'].get('address_line2')}"
                full_address += f", {row['customer_address'].get('city', '')}, {row['customer_address'].get('postcode', '')}"
    
                delivery_address = {
                    "order_id": row['order_id'],
                    "customer_name": row['customer_name'],
                    "customer_phone": row['customer_phone'],
                    "customer_address": full_address,
    
                }
                delivery_addresses.append(delivery_address)
    except Exception as e:
        st.error(f"Error loading orders: {e}")
        return []
    
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
                
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass 

    return delivery_addresses


def load_orders_by_todaysdate(todays_date):
     
    """Load all orders placed for a specific menu"""
    conn = None
    cursor = None
    try:
        conn = get_pg_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Query to get all orders for the specified menu
        query = """
            SELECT order_id, customer_name, customer_phone, customer_address, 
                order_date, delivery_date, items, total, payment_method, 
                status, special_instructions
            FROM orders
            WHERE menu_date = %s and (status not in ('pending','cancelled','rejected'))
            ORDER BY order_date DESC
        """
        cursor.execute(query, (todays_date,))
        results = cursor.fetchall()
        
        orders = []
        for row in results:
            # Convert items from JSONB to Python dict
            items_data = row['items']
            
            order = {
                "order_id": row['order_id'],
                "customer_name": row['customer_name'],
                "customer_phone": row['customer_phone'],
                "customer_address": row['customer_address'],
                "order_date": row['order_date'],
                "delivery_date": row['delivery_date'],
                "items": items_data,
                "total": row['total'],
                "payment_method": row['payment_method'],
                "status": row['status'],
                "special_instructions": row['special_instructions']
            }
            orders.append(order)
        
        return orders
        
    except Exception as e:
        st.error(f"Error loading orders: {e}")
        return []
    
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
                
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

def update_order_status(order_id, status):
    """
    Update the status of an order in the database
    
    Args:
        order_id (str): The ID of the order
        status (str): The new status to set for the order
    """
    conn = None
    cursor = None
    try:
        conn = get_pg_connection()
        cursor = conn.cursor()
        
        # Update the order status in the database
        cursor.execute("""
            UPDATE orders 
            SET status = %s 
            WHERE order_id = %s
        """, (status, order_id))
        
        # Commit the changes
        conn.commit()
        
    except Exception as e:
        st.error(f"Error updating order status: {e}")
        
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
                
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

def get_todays_orders_count(caterer_id):
    """
    Display the total number of orders received today for a specific caterer
    
    Args:
        caterer_id (str): The ID of the caterer
    """
    # Get today's date from session state
    today_date = st.session_state.get('today_date')
    
    # If today's date is not in session state, use current date
    if not today_date:
        from datetime import datetime
        today_date = datetime.now().strftime('%Y-%m-%d')  # Format date as "2025-05-03"
    
    print(f"Today's date: {format_date(today_date)}")
    # Connect to the database
    conn = get_pg_connection()
    cursor = conn.cursor()
    
    try:
        # Query to count orders received today for this caterer based on menu_date
        cursor.execute("""
            SELECT COUNT(*) 
            FROM orders o
            JOIN menu_items m ON o.menu_id = m.menu_id
            WHERE m.caterer_id = %s 
            AND m.menu_date = %s
        """, (caterer_id, today_date))
        
        # Get the count
        result = cursor.fetchone()
        print(f"Count result: {result}")
        count = result['count'] if result['count'] else 0 
        if count is None:
            print("No orders found for today")
            return 0  # Return 0 if no orders found
        return count
    
        # Display the count with an icon
        #st.info(f"📋 **Today's Orders**: {count}")
        
    except Exception as e:
        print(f"Error counting today's orders: {e}")
        return 0  # Return 0 in case of error
        
    finally:
        cursor.close()
        conn.close()
# Function to load all order items for a specific caterer
   
def load_order_items(caterer_id,order_date, status=None):
    """
    Load all order items for a specific caterer from the database
    
    Args:
        caterer_id (str): The ID of the caterer
        
    Returns:
        list: A list of order dictionaries with formatted item strings
    """
    # Connect to the database
    conn = get_pg_connection()
    cursor = conn.cursor()
    print(f"Loading orders for caterer ID: {caterer_id}")
    formatted_order_date = order_date.strftime('%Y-%m-%d')
    try:
        if status and status != "All Orders":
        # Query to get all orders for this caterer
            cursor.execute("""
                SELECT o.order_id, o.customer_name, o.total, o.status,o.items,o.menu_date,o.special_instructions,o.payment_status,o.payment_method
                FROM orders o
                JOIN menu_items m ON o.menu_id = m.menu_id
                WHERE m.caterer_id = %s AND o.status = %s AND  o.menu_date = %s
                ORDER BY o.order_date DESC
            """, (caterer_id,status.lower(),formatted_order_date))
        else:
            # Query without status filter (all orders)
            cursor.execute("""
                SELECT o.order_id, o.customer_name, o.total, o.status, o.items, o.menu_date,o.special_instructions,o.payment_status,o.payment_method
                FROM orders o
                JOIN menu_items m ON o.menu_id = m.menu_id 
                WHERE m.caterer_id = %s AND  o.menu_date = %s
                ORDER BY o.order_date DESC
            """, (caterer_id,formatted_order_date))
        
        orders_data = cursor.fetchall()
        print(f"Orders data: {orders_data}")
        orders = []
        
        for order_data in orders_data:

            # Format items as a string: "Item name x quantity, Item name x quantity"
            items_str = ",\n".join([f"{item_name} x {details['quantity']}" 
                                  for item_name, details in order_data['items'].items()])
            print(f"Formatted items string: {items_str}")
            # Create the order dictionary in the format needed for display
            order = {
                "order_id": order_data['order_id'],
                "customer_name": order_data['customer_name'],
                "items": items_str,
                "total": order_data['total'],
                "status": order_data['status'].lower() ,
                "menu_date": order_data['menu_date'],# Ensure status is lowercase for condition checks
                "special_instructions":order_data['special_instructions'],
                "payment_status":order_data['payment_status'],
                "payment_method":order_data['payment_method']
            }
            
            orders.append(order)
        
        return orders
        
    except Exception as e:
        print(f"Error loading orders: {e}")
        return []
        
    finally:
        cursor.close()
        conn.close()

# Function to check if order exists
def check_order_exists(order_info, menu_id):
    # Database query to check if order exists
    # Return True if exists, False otherwise
    conn = get_pg_connection()
    cursor = conn.cursor()
    query = """
    SELECT * FROM orders
    WHERE menu_id = %s
    AND (
        customer_phone = %s
    )
    """
    
    cursor.execute(
        query, 
        (
            menu_id, 
            order_info.get("customer_phone", "")
        )
    )
    print(f"Query executed: {query}")
    print(f"Query parameters: {menu_id}, {order_info.get('customer_phone', '')}")
    results = cursor.fetchone()
    if results:
        # If order exists, return the order details
        orders = {
            "order_id": results['order_id'],
            "customer_name": results['customer_name'],
            "customer_phone": results['customer_phone'],
            "customer_address": results['customer_address'],
            "order_date": results['order_date'],
            "delivery_date": results['delivery_date'],
            "items": results['items'],
            "total": results['total'],
            "payment_method": results['payment_method'],
            "payment_status":results['payment_status'],
            "status": results['status'],
            "special_instructions": results['special_instructions']
        }
        return orders, True
    else:
        orders = {}
        return orders, False


def save_order_db(order_items, order_info, menu_id,payment_mode,payment_status):
    
    try:    
        with get_pg_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)   
        # Generate a unique order ID
        # Calculate the total order amount
        total_amount = sum(details["price"] * details["quantity"] for details in order_items.values())
        print(f"Total order amount: {total_amount}")
        # Convert the order items to JSONB format
        items_json = {}
        for item_name, details in order_items.items():
            items_json[item_name] = {
                "price": float(details["price"]),
                "quantity": int(details["quantity"]),
                "total": float(details["price"] * details["quantity"])
            }
        
        print(f"Order items JSON: {items_json}")
        print(f"Order info: {order_info}")
        print(f"Menu ID: {menu_id}")    
        # Customer Address in JSON format
        customer_address_json = json.dumps(order_info['customer_address'], indent=4)
        print(f"Customer address JSON: {customer_address_json}")

        # Check if the order already exists
        existing_order_items ,order_exists =check_order_exists(order_info,menu_id) 
        print(f"Existing order items: {existing_order_items}")
        print(f"Order exists: {order_exists}")
        if(order_exists):
            st.error(f"Order with ID  already exists. Do you want to update it?")
            return {}
        # Define the SQL query for inserting the order
        else :
            query = """
            INSERT INTO orders ( 
                menu_id, 
                customer_name, 
                customer_phone, 
                customer_address,
                customer_email,
                menu_date,
                order_date, 
                delivery_date, 
                items, 
                total, 
                payment_method,
                payment_status,
                status, 
                special_instructions
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s,%s) 
            RETURNING order_id 
            """
            
            # Set default values for missing fields in your input data
            delivery_date = order_info.get("delivery_date", None)
            status = order_info.get("status", "pending")  # Default status
            
            # Execute the query with parameters
            cursor.execute(
                query, 
                (
                    menu_id,  
                    order_info['customer_name'],
                    order_info['customer_phone'],               
                    customer_address_json,
                    order_info['customer_email'],
                    order_info['menu_date'],
                    order_info['timestamp'],
                    delivery_date,
                    psycopg2.extras.Json(items_json),
                    total_amount,
                    payment_mode ,
                    payment_status,
                    status,
                    order_info['special_instructions']
                )
            )
            print(f"Query executed: {query}")
            conn.commit()
            result = cursor.fetchone()
            print(f"Result: {result}")
            if result:
                return {"order_id": result[0], "status": "saved"}  # Access the first element of the tuple
            else:
                return {"status": "error", "message": "Failed to insert order"}
            
    except Exception as e:
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e)}")
        st.error(f"Error saving order to database: {str(e)}")
        return {}
