import streamlit as st
import os
from datetime import datetime, timedelta
import uuid
import json
import pandas as pd
import duckdb
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import hashlib
import secrets
import time


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSTGRES_CONFIG = {
    "host": "localhost",
    "database": "mycloudkitchen",
    "user": "postgres",
    "password": "postgres",
    "port": 5432
}

# Cache refresh interval in seconds
CACHE_REFRESH_INTERVAL = 300  # 5 minutes

#  Database connection functions
def get_pg_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(
        host=POSTGRES_CONFIG["host"],
        database=POSTGRES_CONFIG["database"],
        user=POSTGRES_CONFIG["user"],
        password=POSTGRES_CONFIG["password"],
        port=POSTGRES_CONFIG["port"],
        cursor_factory=RealDictCursor
    )

def generate_order_id():
    """Generate a new 4-digit order ID from the sequence"""
    conn = get_pg_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT nextval('order_id_seq')")
    order_id = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    return str(order_id)

def initialize_postgres_database():
    """Initialize PostgreSQL database with required tables"""
    with get_pg_connection() as conn:
        cursor = conn.cursor()
        

        cursor.execute("""
            CREATE SEQUENCE IF NOT EXISTS order_id_seq
                START WITH 1001
                INCREMENT BY 1
                MINVALUE 1001
                MAXVALUE 9999
                CYCLE;
        """)

        cursor.execute("""
            CREATE SEQUENCE IF NOT EXISTS payment_id_seq
                START WITH 1001
                INCREMENT BY 1
                MINVALUE 1001
                MAXVALUE 9999
                CYCLE;
        """)

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email VARCHAR NOT NULL UNIQUE,
                caterer_id INTEGER PRIMARY KEY,
                password VARCHAR NOT NULL,
                password_salt VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                role VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                phone VARCHAR,
                address VARCHAR,
                specialties JSONB,
                bio TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        
        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY DEFAULT nextval('order_id_seq'),
                menu_id VARCHAR NOT NULL,
                customer_name VARCHAR NOT NULL,
                customer_phone VARCHAR,
                customer_address JSONB NOT NULL,
                customer_email VARCHAR,
                menu_date DATE NOT NULL,
                order_date TIMESTAMP NOT NULL,
                delivery_date TIMESTAMP,
                items JSONB NOT NULL,
                total DECIMAL(10,2) NOT NULL,
                payment_method VARCHAR,
                payment_status VARCHAR,
                status VARCHAR NOT NULL,
                special_instructions VARCHAR,
                payment_id integer,
                FOREIGN KEY (menu_id) REFERENCES menu_items(menu_id),
                CONSTRAINT fk_orders_payment FOREIGN KEY (payment_id) REFERENCES payments(payment_id),
                CONSTRAINT unique_order_id UNIQUE (order_id,customer_phone)
                
            )
        """)
        
        # Menu Items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS menu_items (
                menu_id VARCHAR PRIMARY KEY,
                caterer_id INTEGER NOT NULL,
                name VARCHAR NOT NULL,
                orderlink VARCHAR,
                items JSONB NOT NULL,
                menu_date date NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (caterer_id) REFERENCES users(caterer_id)
            )
        """)
        
        # Payments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                        payment_id INTEGER PRIMARY KEY DEFAULT nextval('payment_id_seq'), -- Sequence for all Payments
                        payment_method VARCHAR(50) NOT NULL, -- 'credit_card', 'debit_card', 'paypal', 'stripe','banktransfer' etc.
                        payment_status VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending', 'completed', 'failed', 'refunded', 'cancelled'
                        amount DECIMAL(10,2) NOT NULL,
                        currency VARCHAR(3) NOT NULL DEFAULT 'GBP',
                        payment_intent_id varchar(60), -- Stripe Payment Intent Id
                        transaction_id VARCHAR(255), -- Bank tranfer transaction ID
                        payment_gateway VARCHAR(50), -- 'stripe', 'paypal', 'square', etc.
                        gateway_response TEXT, -- JSON response from payment gateway
                        failure_reason TEXT,
                        processed_at TIMESTAMP WITH TIME ZONE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        
                        -- Foreign key constraint (assuming you have an orders table)
                        CONSTRAINT fk_payments_order FOREIGN KEY (order_id) REFERENCES orders(order_id)
                    )
        """)


        # Menu Catalog Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS menu_catalog (
                menu_item_id INTEGER PRIMARY KEY DEFAULT nextval('menu_item_id_seq'),
                item_name VARCHAR(100) NOT NULL,
                description TEXT,
                default_price DECIMAL(8,2) NOT NULL,
                category VARCHAR(50)
            )       
        """)

        cursor.execute("""
            CREATE SEQUENCE IF NOT EXISTS menu_item_id_seq
                START WITH 1001
                INCREMENT BY 1
                MINVALUE 1001
                MAXVALUE 9999
                CYCLE      
        """)


    conn.commit()



