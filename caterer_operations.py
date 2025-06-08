import psycopg2
import os
from datetime import datetime
from db_operations import get_pg_connection
from restaurant_config import RESTAURANT_CONFIG
import json
import streamlit as st
import pandas as pd
import psycopg2
import psycopg2.extras
import json
from datetime import datetime
from utils import extract_date_from_menu_id,format_date
from admin_operations import get_caterer_by_caterer_id

def update_caterer_profile(caterer_id, updated_info):
    """ Update caterer profile in PostgreSQL then sync to DuckDB"""
    # Check if email exists
    caterer = get_caterer_by_caterer_id(caterer_id)
    if not caterer:
        return False

    with get_pg_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET name = %s, phone = %s, address = %s, specialties = %s, bio = %s
            WHERE caterer_id = %s
        """, (
            updated_info.get("name", caterer["name"]),
            updated_info.get("phone", caterer["phone"]),
            updated_info.get("address", caterer["address"]),
            Json(caterer["specialties"]),  # Assuming specialties is a JSON field
            updated_info.get("bio", caterer["bio"]),
            caterer
        ))
        conn.commit()

        return True
# Function to load all menus for a caterer
def load_caterer_menus(caterer_id):
    """Load all menus published by a specific caterer"""
    conn = None
    cursor = None
    try:
        with get_pg_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        query = """
        SELECT menu_id, name, menu_date, active, orderlink,created_at
        FROM menu_items
        WHERE caterer_id = %s
        ORDER BY created_at DESC
        """
        cursor.execute(query, (caterer_id,))
        results = cursor.fetchall()
        
        menus = []
        for row in results:
            menu = {
                "menu_id": row['menu_id'],
                "name": row['name'],
                "menu_date": row['menu_date'],
                "active": row['active'],
                "orderlink": row['orderlink'],
                "created_at": row['created_at']
            }
            menus.append(menu)
        
        return menus
        
    except Exception as e:
        st.error(f"Error loading menus: {e}")
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


# Function to load detailed menu information
def load_menu_details(menu_id):
    """Load detailed information for a specific menu"""
    conn = None
    cursor = None
    try:
        with get_pg_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        query = """
        SELECT menu_id, caterer_id, name, orderlink, items, menu_date, active, created_at
        FROM menu_items
        WHERE menu_id = %s
        """
        cursor.execute(query, (menu_id,))
        result = cursor.fetchone()
        
        if result is None:
            return None
        
        menu = {
            "menu_id": result['menu_id'],
            "caterer_id": result['caterer_id'],
            "name": result['name'],
            "orderlink": result['orderlink'],
            "items": result['items'],
            "menu_date": result['menu_date'],
            "active": result['active'],
            "created_at": result['created_at']
        }
        return menu
        
    except Exception as e:
        st.error(f"Error loading menu details: {e}")
        return None
    
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

def update_menu_items_db(menu_df,menu_date):
    
    try:    
        with get_pg_connection() as conn:
            cursor = conn.cursor()
            # Convert menu DataFrame to a list of dictionaries for JSON storage
            menu_items = []
            for index, row in menu_df.iterrows():
                menu_items.append({
                    "item_name": row['Item'],
                    "price": float(row['Price'])
                })
            print(f"Menu Items : {menu_items}")
            print(f"Menu Date :{menu_date}")
            cursor.execute("""
                UPDATE menu_items 
                SET items = %s 
                WHERE menu_date = %s
                """, (psycopg2.extras.Json(menu_items), menu_date))
        
            conn.commit()
            return True
    except Exception as e:
    # Log the error and rollback
        print(f"Database error: {str(e)}")
        if conn:
            conn.rollback()
        raise e
    return False

def save_menu_db(menu_df, menu_id,order_link,menu_date,caterer_id):
    try:    
        with get_pg_connection() as conn:
            cursor = conn.cursor()

            # Convert menu DataFrame to a list of dictionaries for JSON storage
            menu_items = []
            for index, row in menu_df.iterrows():
                menu_items.append({
                    "item_name": row['Item'],
                    "price": float(row['Price'])
                })
            
            menu_name = f"{menu_id}_{RESTAURANT_CONFIG['name']}"
            orderlink = f"{order_link}"
            formatted_menu_date = menu_date.strftime('%Y-%m-%d')
            # Convert the list to a JSON string
            items_json = json.dumps(menu_items)
            # Insert or update the menu record
            cursor.execute(
                """
                INSERT INTO menu_items 
                (menu_id, caterer_id, name, orderlink,items, menu_date,active ,created_at) 
                VALUES (%s, %s, %s, %s, %s,%s, %s, %s)
                ON CONFLICT (menu_id) DO UPDATE 
                SET caterer_id = EXCLUDED.caterer_id,
                    name = EXCLUDED.name,
                    orderlink= EXCLUDED.orderlink,
                    items = EXCLUDED.items,
                    menu_date = EXCLUDED.menu_date,
                    active = EXCLUDED.active,
                    created_at = EXCLUDED.created_at
                RETURNING menu_id
                """,
                (menu_id, caterer_id, menu_name,orderlink,psycopg2.extras.Json(menu_items),formatted_menu_date,True, datetime.now())
            )
            
            conn.commit()

            # Return the URL to view the menu
            menu_url = f"/view_menu?menu_id={menu_id}"
            return menu_url
        
    except Exception as e:
        # Log the error and rollback
        print(f"Database error: {str(e)}")
        if conn:
            conn.rollback()
        raise e
        
    finally:
        # Close cursor and connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return None 

def load_menu_from_db(menu_id=None, caterer_id=None):
    """
    Load menu data from PostgreSQL database.
    Can retrieve by menu_id (returns single menu) or caterer_id (returns all menus for a caterer).
    At least one parameter must be provided.
    
    Returns:
    - If menu_id is provided: A single menu dict or None if not found
    - If only caterer_id is provided: A list of menu dicts or empty list if none found
    """
    # Input validation
    if menu_id is None and caterer_id is None:
        raise ValueError("Either menu_id or caterer_id must be provided")
    try: 
    # Connect to PostgreSQL
        with get_pg_connection() as conn:
            cursor = conn.cursor()
            try:
                # Define query based on input parameters
                if menu_id is not None:
                    # Get a specific menu
                    query = """
                    SELECT menu_id, caterer_id, name, orderlink,items, menu_date,active,created_at
                    FROM menu_items
                    WHERE menu_id = %s
                    """
                    cursor.execute(query, (menu_id,))
                    result = cursor.fetchone()
                    print(f"Result: {result}")
                    if result is None:
                        print(f"No menu found with menu_id: {menu_id}")
                        return None
                    
                    # Convert row to dictionary
                    menu = {
                        "menu_id": result['menu_id'],
                        "caterer_id": result['caterer_id'],
                        "name": result['name'],
                        "orderlink": result['orderlink'],
                        "items": result['items'],
                        "menu_date": result['menu_date'],
                        "active": result['active'],
                        "created_at": result['created_at']
                    }
                    print(f"Loaded menu: {menu}")
                    return menu
                    
                else:
                    # Get all menus for a caterer
                    query = """
                    SELECT menu_id, caterer_id, name, orderlink,items, menu_date,active,created_at
                    FROM menu_items
                    WHERE caterer_id = %s
                    ORDER BY created_at DESC
                    """
                    cursor.execute(query, (caterer_id,))
                    results = cursor.fetchall()
                    
                    menus = []
                    for row in results:
                        menu = {
                            "menu_id": result[0],
                            "caterer_id": result[1],
                            "name": result[2],
                            "orderlink": result[3],
                            "items": json.loads(result[4]) if result[4] else {},
                            "menu_date": result[5],
                            "active": result[6],
                            "created_at": result[7]
                        }
                        menus.append(menu)
                    
                    return menus
        
            except Exception as e:
                print(f"Error loading menu from database: {e}")
                return None
            
    except psycopg2.Error as db_error:
        print(f"Database error: {db_error}")
        return None
    
    
        