import gspread
from datetime import datetime
from gsheets_processing import connect_to_gsheets

def save_restaurant_profile_to_sheets(profile_data):
    """Save restaurant profile to Google Sheets"""
    gc = connect_to_gsheets()
    
    try:
        # Try to open existing profiles sheet
        sheet = gc.open("Restaurant_Profiles")
    except gspread.SpreadsheetNotFound:
        # Create new sheet if it doesn't exist
        sheet = gc.create("Restaurant_Profiles")
        worksheet = sheet.sheet1
        
        # Set up headers
        headers = ["id", "name", "address", "phone", "email", "currency", 
                  "logo_url", "theme_color", "description", "created_at", "updated_at"]
        worksheet.append_row(headers)
    else:
        worksheet = sheet.sheet1
    
    # Check if profile exists (update) or is new (insert)
    restaurant_id = profile_data.get("id", str(int(datetime.now().timestamp())))
    profile_data["id"] = restaurant_id
    
    # Add timestamps
    now = datetime.now().isoformat()
    if "created_at" not in profile_data:
        profile_data["created_at"] = now
    profile_data["updated_at"] = now
    
    # Find if profile exists
    try:
        cell = worksheet.find(restaurant_id)
        row_values = worksheet.row_values(cell.row)
        headers = worksheet.row_values(1)
        
        # Update existing row
        for col, header in enumerate(headers, start=1):
            if header in profile_data:
                worksheet.update_cell(cell.row, col, profile_data[header])
    except gspread.exceptions.CellNotFound:
        # Insert new row
        row = [profile_data.get(header, "") for header in worksheet.row_values(1)]
        worksheet.append_row(row)
    
    return restaurant_id


    