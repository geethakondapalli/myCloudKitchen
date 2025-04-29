import re

def validate_name(name):
    """Validate customer name"""
    if not name.strip():
        return False, "Name is required"
    return True, ""

def validate_phone(phone):
    """Validate phone number"""
    if not phone.strip():
        return False, "Phone number is required"
    phone_pattern = r"^((\+44|0044|0)7\d{9})$"
    if not re.match(phone_pattern, phone):
        return False, "Please enter a valid UK mobile number"
    return True, ""

def validate_email(email, required=False):
    """Validate email"""
    if required and not email.strip():
        return False, "Email is required for invoice generation"
    if email.strip():
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            return False, "Please enter a valid email address"
    return True, ""