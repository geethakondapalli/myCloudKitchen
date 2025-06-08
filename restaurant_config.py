# Restaurant Configuration
RESTAURANT_CONFIG = {
    "name": "Flavours of India",
    "emoji": "🍽️",
    "currency": "£",
    "pickup address":""

}

# Additional configuration options
MENU_OPTIONS = {
    "allow_special_requests": True,
    "show_dish_categories": False,
    "max_quantity_per_item": 10
}

# Admin options
ADMIN_CONFIG = {
    "enable_image_upload": True,
    "manual_menu_entry": True,
    "admin_emails": ["geethakondapalli6@gmail.com", "ashokd23@gmail.com"],
    "base_url" : "http://localhost:8509"
}

date_formats = [
    '%d/%m/%Y',       # 23/04/2025
    '%m/%d/%Y',       # 04/23/2025
    '%d-%m-%Y',       # 23-04-2025
    '%m-%d-%Y',       # 04-23-2025
    '%B %d, %Y',      # April 23, 2025
    '%d %B %Y',       # 23 April 2025
    '%d-%b-%y',       # 1-APR-25 (this is the one you need)
    '%d-%b-%Y',       # 1-APR-2025
    '%d/%b/%y',       # 1/APR/25
    '%d/%b/%Y'        # 1/APR/2025
]
