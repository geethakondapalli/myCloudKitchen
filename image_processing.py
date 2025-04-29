import pytesseract
import pandas as pd
from restaurant_config import RESTAURANT_CONFIG, ADMIN_CONFIG
import re
from datetime import datetime

# Enhance image preprocessing specifically for highlighted text
def preprocess_for_highlighted_text(image):
    """Apply specialized preprocessing for highlighted text areas"""
    # Convert to grayscale
    gray = image.convert('L')
    
    # Try different threshold values that might work better for highlighted text
    enhanced_images = []
    
    # Add original image
    enhanced_images.append(image)
    
    # Add grayscale
    enhanced_images.append(gray)
    
    # Try multiple threshold values to handle highlighted backgrounds
    for threshold in [80, 100, 120, 140, 160, 180, 200, 220]:
        binary = gray.point(lambda p: 255 if p > threshold else 0)
        enhanced_images.append(binary)
    
    return enhanced_images

#  Add this to your image processing pipeline
def extract_highlighted_text(image):
    """Attempt to extract text with a focus on highlighted areas"""
    enhanced_images = preprocess_for_highlighted_text(image)
    
    all_text = ""
    for img in enhanced_images:
        try:
            # Try different OCR configurations
            for config in ['--psm 6', '--psm 11', '--psm 4']:
                text = pytesseract.image_to_string(img, config=config)
                all_text += text + "\n"
        except Exception:
            continue
    
    return all_text

def extract_menu_from_image(image):
    """Extract menu items, prices, and date from an uploaded image
    Returns: (menu_dataframe, extracted_date_string, success_flag)
    """

# First, get text from regular OCR
    regular_text = pytesseract.image_to_string(image)
    regular_lines = [line.strip() for line in regular_text.splitlines() if line.strip()]

    # Then, get additional text from highlighted areas (using your specialized function)
    highlighted_text = extract_highlighted_text(image)
    highlighted_lines = [line.strip() for line in highlighted_text.splitlines() if line.strip()]


# Debug: print the first few lines to see what's being found
    for line in highlighted_text[:5]:
        print(f"Debug line: {line}")
        # Try to find a date in the menu text
    menu_date = None
    date_patterns = [
        # Various date formats
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # DD/MM/YYYY or MM/DD/YYYY
        r'.*\((\d{1,2}-\w{3}-\d{2,4})\)',  # 13-APR-2025 or 13/APR/2025
        r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{2,4})',  # 21st January 2023
        r'((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{2,4})',  # January 21, 2023
        r'((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})'  # January 2023
    ]
    
    # Search first 10 lines for a date (likely to be in header)
    for line in highlighted_lines:
        print(f"Debug: {line}")
        for pattern in date_patterns:
            date_match = re.search(pattern, line, re.IGNORECASE)
            if date_match:
                menu_date = date_match.group(1)
                break
        if menu_date:
            print(f"Debug: Found date: {menu_date}")
            break
    
    # If no date found, use today's date
    if not menu_date:
        menu_date = datetime.now().strftime("%d/%m/%Y")
    
    # Extract menu items
    menu_items = []
    currency_symbol = RESTAURANT_CONFIG['currency']
    price_pattern = rf"(.+?)\s*[-–—]\s*{re.escape(currency_symbol)}\s*(\d+(?:\.\d{1,2})?)"
    
    for line in regular_lines:
        match = re.match(price_pattern, line, re.IGNORECASE)
        if match:
            item = match.group(1).strip()
            price = float(match.group(2).strip())
            menu_items.append({"Item": item, "Price": price})
    
    # Create the DataFrame
    menu_df = pd.DataFrame(menu_items)
    
    return menu_df, menu_date, bool(menu_items)
