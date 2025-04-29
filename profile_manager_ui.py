import streamlit as st
from kitchen_profile import save_restaurant_profile, load_restaurant_profile, get_all_restaurants
from datetime import datetime

def restaurant_profile_manager():
    """Restaurant profile management UI"""
    st.title("Restaurant Profile Manager")
    
    # Sidebar for navigation
    action = st.sidebar.radio("Actions", ["Create New Profile", "Edit Existing Profile", "View All Profiles"])
    
    if action == "Create New Profile":
        st.header("Create New Restaurant Profile")
        
        # Basic info
        with st.form("profile_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Restaurant Name*")
                address = st.text_area("Address*")
                phone = st.text_input("Phone Number*")
            
            with col2:
                email = st.text_input("Email")
                currency = st.selectbox("Currency", ["£", "$", "€", "¥", "₹"], index=0)
                logo = st.file_uploader("Restaurant Logo", type=["jpg", "png", "jpeg"])
            
            # Theme customization
            theme_color = st.color_picker("Theme Color", "#FF4B4B")
            description = st.text_area("Restaurant Description")
            
            # Additional settings
            st.subheader("Menu Settings")
            default_categories = st.text_input("Default Menu Categories (comma separated)", 
                                            "Starters, Main Course, Desserts, Drinks")
            
            submitted = st.form_submit_button("Save Profile")
            
            if submitted:
                if not name or not address or not phone:
                    st.error("Please fill all required fields marked with *")
                else:
                    # Save logo if uploaded
                    logo_path = None
                    if logo:
                        os.makedirs("restaurant_logos", exist_ok=True)
                        logo_path = f"restaurant_logos/{name.lower().replace(' ', '_')}.png"
                        with open(logo_path, "wb") as f:
                            f.write(logo.getbuffer())
                    
                    # Create profile data
                    profile_data = {
                        "name": name,
                        "address": address,
                        "phone": phone,
                        "email": email,
                        "currency": currency,
                        "logo_url": logo_path,
                        "theme_color": theme_color,
                        "description": description,
                        "menu_categories": [cat.strip() for cat in default_categories.split(",")],
                        "created_at": datetime.now().isoformat()
                    }
                    
                    # Save profile
                    restaurant_id = save_restaurant_profile(profile_data)
                    st.success(f"Restaurant profile created successfully! ID: {restaurant_id}")
                    
                    # Store in session state
                    st.session_state.current_restaurant_id = restaurant_id

    elif action == "Edit Existing Profile":
        # Load and edit existing profile
        profiles = get_all_restaurants()
        if not profiles:
            st.info("No restaurant profiles found. Create one first.")
        else:
            profile_names = [p.get("name", f"Restaurant {p.get('id')}") for p in profiles]
            selected_profile = st.selectbox("Select Restaurant", profile_names)
            
            # Find selected profile
            profile = next((p for p in profiles if p.get("name") == selected_profile), None)
            
            if profile:
                # Display edit form pre-filled with existing data
                # [Edit form code similar to create form but pre-filled]
                pass