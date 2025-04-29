import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import io
import re
from datetime import datetime
import os
from urllib.parse import urlencode

st.set_page_config(page_title="Flavors of India - Admin & Order Form")

# Read query parameters
params = st.query_params
print("Debug" + str(params))
menu_id = params["menu_id"]  if "menu_id" in params else None
print(menu_id)
def extract_menu_from_image(image):
    text = pytesseract.image_to_string(image)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    menu_items = []
    for line in lines:
        match = re.match(r"(.+?)\s*[-–—]\s*£\s*(\d+(?:\.\d{1,2})?)", line, re.IGNORECASE)
        if match:
            item = match.group(1).strip()
            price = float(match.group(2).strip())
            menu_items.append({"Item": item, "Price": price})
    return pd.DataFrame(menu_items)

def save_menu(menu_df, menu_id):
    menu_df.to_csv(f"menu_{menu_id}.csv", index=False)

def load_menu(menu_id):
    print("Debug" + os.getcwd())
    if not os.path.exists(f"menu_{menu_id}.csv"):
        st.error("Menu not found. Please upload a menu first.")
        return pd.DataFrame()
    return pd.read_csv(f"menu_{menu_id}.csv")

st.title("🍽️ Flavors of India")

# --- ADMIN MODE ---
if menu_id is None:
    st.header("👩‍💼 Admin Panel - Upload Menu")

    uploaded_image = st.file_uploader("Upload Menu Image", type=["png", "jpg", "jpeg"])

    if uploaded_image:
        image = Image.open(uploaded_image)
        st.image(image, caption="Uploaded Menu", use_column_width=True)

        menu_df = extract_menu_from_image(image)

        if not menu_df.empty:
            st.success("Menu Extracted Successfully!")
            st.dataframe(menu_df)

            if st.button("Save Menu & Generate Link"):
                # Generate a random simple menu ID
                menu_id = str(int(datetime.now().timestamp()))
                save_menu(menu_df, menu_id)

                # Generate link
               # base_url = "https://your-app-name.streamlit.app"  # <- your deployed Streamlit app URL
            
                base_url = "http://localhost:8509"  # <- your local Streamlit app URL
                order_link = f"{base_url}?menu_id={menu_id}"

                st.success("✅ Order Form Link Generated!")
                st.markdown(f"[🔗 Click Here to View Order Form]({order_link})")
                st.code(order_link)

# --- CUSTOMER ORDER MODE ---
else:
    st.header("🛒 Place Your Order")

    try:
        print("Debug"+ menu_id)
        menu_df = load_menu(menu_id)
        st.success("Menu Loaded Successfully!")

        customer_name = st.text_input("Enter Your Name")
        order = {}
        for index, row in menu_df.iterrows():
            qty = st.number_input(f"{row['Item']} (£{row['Price']:.2f})", min_value=0, step=1, key=index)
            if qty > 0:
                order[row['Item']] = {"price": row['Price'], "quantity": qty}

        if st.button("Submit Order"):
            if not customer_name:
                st.warning("Please enter your name.")
            elif not order:
                st.warning("Please select at least one item.")
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                total = sum(details['price'] * details['quantity'] for details in order.values())

                order_data = {
                    "Timestamp": timestamp,
                    "Customer Name": customer_name,
                    "Menu ID": menu_id,
                    "Items": "; ".join([f"{item} x {details['quantity']}" for item, details in order.items()]),
                    "Total (£)": total
                }

                # Save the order
                order_file = f"orders_{menu_id}.csv"
                if not os.path.exists(order_file):
                    df = pd.DataFrame(columns=order_data.keys())
                    df.to_csv(order_file, index=False)

                df = pd.read_csv(order_file)
                df = pd.concat([df, pd.DataFrame([order_data])], ignore_index=True)
                df.to_csv(order_file, index=False)

                st.success("✅ Order Submitted Successfully! Thank you!")

    except Exception as e:
        st.error(f"Error loading menu: {str(e)}")
