from db_operations import get_pg_connection
from psycopg2.extras import Json


def update_caterer_status(caterer_id, status):
    """Update caterer status in PostgreSQL """
    with get_pg_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = %s WHERE email = %s", (status, caterer_id))
        conn.commit()

    return True

# User management functions
def get_all_caterers():
   
    """Get all caterers from PostgreSQL database"""
    with get_pg_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE role = 'caterer'")
            caterers = cursor.fetchall()
            
        # Convert to list of dictionaries
        if caterers:
            print(f"Fetched caterers: {caterers}")  # Debugging line
            return caterers
        else:
            return []

def get_caterer_by_caterer_id(caterer_id):
    
    with get_pg_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE caterer_id = %s", [caterer_id])
            caterer = cursor.fetchone()
        if caterer:
            return caterer
        return None
    
# User management functions
def get_all_caterers():
   
    """Get all caterers from PostgreSQL database"""
    with get_pg_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE role = 'caterer'")
            caterers = cursor.fetchall()
            
        # Convert to list of dictionaries
        if caterers:
            print(f"Fetched caterers: {caterers}")  # Debugging line
            return caterers
        else:
            return []