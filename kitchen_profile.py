import json
import os
import streamlit as st
from datetime import datetime

# Define the profiles directory
PROFILES_DIR = "restaurant_profiles"
os.makedirs(PROFILES_DIR, exist_ok=True)

def save_restaurant_profile(profile_data):
    """Save restaurant profile to a JSON file"""
    restaurant_id = profile_data.get("id", str(int(datetime.now().timestamp())))
    profile_data["id"] = restaurant_id
    
    file_path = os.path.join(PROFILES_DIR, f"{restaurant_id}.json")
    with open(file_path, 'w') as f:
        json.dump(profile_data, f, indent=2)
    
    return restaurant_id

def load_restaurant_profile(restaurant_id):
    """Load restaurant profile from JSON file"""
    file_path = os.path.join(PROFILES_DIR, f"{restaurant_id}.json")
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def get_all_restaurants():
    """Get a list of all restaurant profiles"""
    restaurants = []
    for filename in os.listdir(PROFILES_DIR):
        if filename.endswith('.json'):
            file_path = os.path.join(PROFILES_DIR, filename)
            with open(file_path, 'r') as f:
                restaurants.append(json.load(f))
    return restaurants