import streamlit as st
from datetime import datetime
from db_operations import get_pg_connection


def display_payments():
    """Display Payment statues for a Menu or a shipment date"""
    st.subheader("View Payments")
    # Load orders from database
    col1,col3 = st.columns([1, 4])
    with col1:
        payment_sel_input = st.date_input(
                            "Select Date",
                            value= datetime.today(),
                            format="DD/MM/YYYY",
                    )
    
    # Filter tabs
    tabs = st.tabs(["All Payments", "Payment Success" ,"Payment Pending", "Payment Failed"])
    
    with tabs[0]:
        payments = load_payment_status(payment_sel_input)
        display_payment_status(payments)

    with tabs[1]:
        payments = load_payment_status(payment_sel_input, "Payment Success")
        display_payment_status(payments, tab_name=tabs[1])

    with tabs[2]:
        payments= load_payment_status(payment_sel_input, "Payment Pending")
        display_payment_status(payments,tabs[2])

    with tabs[3]:
        payments= load_payment_status(payment_sel_input, "Payment Failed")
        display_payment_status(payments,tabs[3])


def display_payment_status(payments,tab_name="All Payments"):
    """Display Payment Statues """
    if not payments:
        st.info(f"No orders found.")
        return
    for payment in payments:
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                col1.write(f"**{payment['order_id']} - {payment['customer_name']}**")
                col1.write(f"Payment Status:{payment['payment_status']}")
                col1.write(f"Payment Method :{payment['payment_method']}")
                #col2.write(f"**Total Amount:** ₹{payment['amount']}")
                col2.write(f"**Order Status:** {payment['status']}")
                button_key = f"{tab_name}_payrecv_{payment['order_id']}"
                if button_key not in st.session_state:   
                    st.session_state[button_key] = False
                # Only show button if it hasn't been clicked
                if not st.session_state[button_key]:
                    if col2.button("Payment Received", key=f"btn_{button_key}"):
                        st.session_state[button_key] = True
                        st.success("Payment Received")
                        st.rerun()  # Refresh the app to hide the button
                else:
                # Optionally show a message or different content where the button was
                    col2.write("✅ Payment Received")
                st.divider() 
                """ # Action buttons based on status
                if order["status"] == "pending":
                    col3_left, col3_right = col3.columns(2)
                    if col3_left.button("Accept", key=f"{tab_name}_accept_{order['order_id']}"):
                        # Update order status in database
                        update_order_status(order['order_id'], "accepted")
                        st.success(f"Order {order['order_id']} Accepted!")
                    if col3_right.button("Reject", key=f"{tab_name}_reject_{order['order_id']}"):
                        update_order_status(order['order_id'], "rejected")
                        st.success(f"Order {order['order_id']} Rejected!")
                elif order["status"] == "accepted":
                    col3_left, col3_right = col3.columns(2)
                    if col3_left.button("Mark Ready", key=f"{tab_name}_ready_{order['order_id']}"):
                        update_order_status(order['order_id'], "ready")
                        st.success(f"Order {order['order_id']} Mark as ready!")
                    if col3_right.button("Cancel", key=f"{tab_name}_cancel_accepted_{order['order_id']}"):
                        update_order_status(order['order_id'], "cancelled")
                        st.success(f"Order {order['order_id']} Cancelled!")
                elif order["status"] == "ready":
                    col3_left, col3_right = col3.columns(2)
                    if col3_left.button("Complete", key=f"{tab_name}_complete_{order['order_id']}"):
                        update_order_status(order['order_id'], "completed")
                        st.success(f"Order {order['order_id']} completed!")
                    if col3_right.button("Cancel", key=f"{tab_name}_cancel_ready_{order['order_id']}"):
                        update_order_status(order['order_id'], "cancelled")
                        st.success(f"Order {order['order_id']} Cancelled!")
                elif order["status"] == "cancelled":
                    col3.write("Order Cancelled - No action required")
                elif order["status"] == "completed":
                    col3.write("Order Completed - No action required")
                elif order["status"] == "rejected":
                    col3.write("Order Rejected - No action required")
                st.divider() """



def load_payment_status(order_date, status=None):
    """
    Load all payment status for a specific caterer from the database
    
    Args:
        caterer_id (str): The ID of the caterer
        
    Returns:
        list: A list of order dictionaries with formatted item strings
    """
    # Connect to the database
    conn = get_pg_connection()
    cursor = conn.cursor()

    formatted_order_date = order_date.strftime('%Y-%m-%d')
    try:
        if status and status != "All Payments":
        # Query to get all orders for this caterer
            cursor.execute("""
                SELECT o.order_id, o.customer_name, o.total, o.status,o.payment_status,o.payment_method
                FROM orders o
                WHERE o.menu_date = %s and o.payment_status=%s
                ORDER BY o.order_date DESC
            """, (formatted_order_date,status)
            )
        else:
            # Query without status filter (all orders)
            cursor.execute("""
                SELECT o.order_id, o.customer_name, o.total, o.status,o.payment_status,o.payment_method
                FROM orders o
                WHERE o.menu_date = %s
                ORDER BY o.order_date DESC
            """, (formatted_order_date))
        
        payments_data = cursor.fetchall()
        print(f"Payments data: {payments_data}")
        payments= []
        
        for payment in payments_data:

            payment = {
                "order_id": payment['order_id'],
                "customer_name": payment['customer_name'],
                "amount":str(payment['total']),
                "status": payment['status'].lower() ,
                "payment_status":payment['payment_status'],
                "payment_method":payment['payment_method']
            }
            
            payments.append(payment)
        
        return payments
        
    except Exception as e:
        print(f"Error loading orders: {e}")
        return []
        
    finally:
        cursor.close()
        conn.close()


