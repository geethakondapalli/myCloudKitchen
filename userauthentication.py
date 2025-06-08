

# Authentication functions
def login(email, password):
    """Authenticate user login - use DuckDB for faster authentication"""
    check_and_refresh_cache()
    
    with get_duckdb_connection() as conn:
        result = conn.execute("SELECT * FROM users WHERE email = ?", [email]).fetchone()
        if result:
            user = dict(zip(result.keys(), result))
            password_hash = hash_password(password, user["password_salt"])
            
            if user["password"] == password_hash:
                st.session_state.authenticated = True
                st.session_state.current_user = email
                st.session_state.current_role = user["role"]
                
                # Set initial page based on role
                if user["role"] == "admin":
                    st.session_state.page = "admin_dashboard"
                else:
                    st.session_state.page = "caterer_dashboard"
                
                return True
    
    return False