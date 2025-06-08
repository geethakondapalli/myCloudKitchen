import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import calendar
from datetime import datetime as dt, date, timedelta


# Sample data generation function (replace with your actual data source)
def generate_sample_orders(days=90, orders_per_day=5):
    np.random.seed(42)  # For reproducible results
    
    orders = []
    today = dt.now().date()
    
    # Common menu items and their price ranges
    menu_items = {
        "Chicken Majestic": (5, 6),
        "Chicken Briyani": (6 , 7),
        "Veg Biryani": (4, 5),
        "Paneer": (8, 9),
        "NV Combo": (13, 15),
        "Veg Combo": (10, 11)
    }
    
    # Payment methods
    payment_methods = ["Credit Card", "Bank Transfer", "PayPal", "Cash"]
    
    # Generate orders for each day
    for day_offset in range(days):
        order_date = today - timedelta(days=day_offset)
        
        
        # Vary the number of orders per day (weekends have more orders)
        weekday = order_date.weekday()
        if weekday >= 5:  # Weekend
            day_orders = int(orders_per_day * 1.5)
        else:
            day_orders = orders_per_day
            
        for _ in range(day_orders):
            # Select a random menu item
            menu_name = np.random.choice(list(menu_items.keys()))
            min_price, max_price = menu_items[menu_name]
            
            # Generate a total price
            total = round(np.random.uniform(min_price, max_price), 2)
            
            # Add some seasonal variation
            month = order_date.month
            if month in [11, 12]:  # Holiday season
                total *= 1.2
            elif month in [5, 6]:  # Wedding season
                total *= 1.1
            
            # Create the order
            order = {
                "order_id": f"ORD-{len(orders) + 1:04d}",
                "order_date": order_date,
                "menu_name": menu_name,
                "total": total,
                "payment_method": np.random.choice(payment_methods),
                "status": np.random.choice(["completed", "cancelled", "pending"], p=[0.85, 0.05, 0.1])
            }
            
            # Don't include cancelled orders in the earnings
            if order["status"] != "cancelled":
                orders.append(order)
        print(f"Generated Order :{orders}")
    return orders

# Helper functions for data processing
def group_by_date(orders, date_col='order_date'):
    """Group orders by date and calculate totals"""
    daily_totals = {}
    
    for order in orders:
        date = order[date_col]
        if date not in daily_totals:
            daily_totals[date] = 0
        daily_totals[date] += order['total']
    
    # Convert to DataFrame
    df = pd.DataFrame({
        'Date': list(daily_totals.keys()),
        'Total': list(daily_totals.values())
    })
    df['Date'] = pd.to_datetime(df['Date'])
    return df.sort_values('Date')

def group_by_month(orders, date_col='order_date'):
    """Group orders by month and calculate totals"""
    monthly_totals = {}
    
    for order in orders:
        date = order[date_col]
        if isinstance(date, str):
            date = dt.strptime(date, '%Y-%m-%d').date()
        
        month_key = f"{date.year}-{date.month:02d}"
        if month_key not in monthly_totals:
            monthly_totals[month_key] = 0
        monthly_totals[month_key] += order['total']
    
    # Convert to DataFrame
    df = pd.DataFrame({
        'Month': list(monthly_totals.keys()),
        'Total': list(monthly_totals.values())
    })
    return df.sort_values('Month')

def group_by_menu(orders):
    """Group orders by menu type and calculate totals"""
    menu_totals = {}
    
    for order in orders:
        menu = order['menu_name']
        if menu not in menu_totals:
            menu_totals[menu] = 0
        menu_totals[menu] += order['total']
    
    # Convert to DataFrame
    df = pd.DataFrame({
        'Menu': list(menu_totals.keys()),
        'Total': list(menu_totals.values())
    })
    return df.sort_values('Total', ascending=False)

def group_by_payment_method(orders):
    """Group orders by payment method and calculate totals"""
    payment_totals = {}
    
    for order in orders:
        payment = order['payment_method']
        if payment not in payment_totals:
            payment_totals[payment] = 0
        payment_totals[payment] += order['total']
    
    # Convert to DataFrame
    df = pd.DataFrame({
        'Payment Method': list(payment_totals.keys()),
        'Total': list(payment_totals.values())
    })
    return df.sort_values('Total', ascending=False)

def format_currency(amount):
    """Format amount as currency"""
    return f"£{amount:,.2f}"

def display_payments():
    
    return True
# Main dashboard
def display_revenue_dashboard():
    # Title and description
    st.title("💰 Earnings Dashboard")
    st.markdown("Track your catering business revenue with detailed visualizations and analytics. Mock up data")
    
    # Generate sample data (replace with your actual data loading)
    orders = generate_sample_orders()
    
    # Date filter
    st.sidebar.header("Filter Data")
    
    # Date range selector
    date_options = ["Last 7 days", "Last 30 days", "Last 90 days", "Year to date", "All time", "Custom range"]
    date_filter = st.sidebar.selectbox("Date Range", date_options)
    
    # Today's date for reference
    today = dt.now().date()
    
    # Calculate filter dates
    if date_filter == "Last 7 days":
        start_date = today - timedelta(days=7)
        end_date = today
    elif date_filter == "Last 30 days":
        start_date = today - timedelta(days=30)
        end_date = today
    elif date_filter == "Last 90 days":
        start_date = today - timedelta(days=90)
        end_date = today
    elif date_filter == "Year to date":
        start_date = dt(today.year, 1, 1).date()
        end_date = today
    elif date_filter == "All time":
        # Use the earliest date in the dataset
        start_date = min(order['order_date'] for order in orders)
        end_date = today
    else:  # Custom range
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=today - timedelta(days=30))
        with col2:
            end_date = st.date_input("End Date", value=today)
    
    print("Type of date:", type(date))
    print("Is date a type?", isinstance(date, type))
    # Filter orders by date
    filtered_orders = [
        order for order in orders 
        if isinstance(order['order_date'], type(dt.date)) and start_date <= order['order_date'] <= end_date
    ]

            
    # Top metrics
    st.header("Key Performance Indicators")
    
    # Calculate KPIs
    total_earnings = sum(order['total'] for order in orders)
    order_count = len(orders)
    avg_order_value = total_earnings / order_count if order_count > 0 else 0
    
    # Calculate the same period in the previous time range for comparison
    date_diff = (end_date - start_date).days + 1
    prev_end_date = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=date_diff - 1)
    
    prev_filtered_orders = [
        order for order in orders 
        if isinstance(order['order_date'], type(dt.date)) and prev_start_date <= order['order_date'] <= prev_end_date
    ]
    
    prev_total_earnings = sum(order['total'] for order in prev_filtered_orders)
    prev_order_count = len(prev_filtered_orders)
    
    # Calculate changes
    earnings_change = ((total_earnings - prev_total_earnings) / prev_total_earnings * 100) if prev_total_earnings > 0 else 0
    orders_change = ((order_count - prev_order_count) / prev_order_count * 100) if prev_order_count > 0 else 0
    
    # Display KPIs in columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Total Revenue", 
            value=format_currency(total_earnings),
            delta=f"{earnings_change:.1f}%" if earnings_change != 0 else None
        )
    
    with col2:
        st.metric(
            label="Total Orders", 
            value=f"{order_count:,}",
            delta=f"{orders_change:.1f}%" if orders_change != 0 else None
        )
    
    with col3:
        st.metric(
            label="Average Order Value", 
            value=format_currency(avg_order_value)
        )
    
    # Revenue charts
    st.header("Revenue Trends")
    chart_tabs = st.tabs(["Daily", "Monthly", "Menu Analysis", "Payment Methods"])
    
    # Daily revenue chart
    with chart_tabs[0]:
        daily_df = group_by_date(orders)
        
        if not daily_df.empty:
            # Smooth the data with rolling average
            daily_df['7-Day Rolling Avg'] = daily_df['Total'].rolling(window=7, min_periods=1).mean()
            
            # Create figure
            fig = px.line(
                daily_df, 
                x='Date', 
                y=['Total', '7-Day Rolling Avg'],
                title='Daily Revenue',
                labels={'value': 'Revenue', 'variable': 'Series'},
                color_discrete_map={'Total': '#FF6B6B', '7-Day Rolling Avg': '#4ECDC4'}
            )
            fig.update_layout(
                xaxis_title='Date',
                yaxis_title='Revenue (£)',
                legend_title='',
                hovermode='x unified'
            )
            
            # Add currency to hover
            fig.update_traces(
                hovertemplate='%{y:£,.2f}'
            )
            
            # Format y-axis as currency
            fig.update_layout(
                yaxis=dict(
                    tickprefix='£',
                    separatethousands=True
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show daily revenue table
            with st.expander("Show Daily Revenue Table"):
                daily_df['Date'] = daily_df['Date'].dt.date
                daily_df['Total'] = daily_df['Total'].apply(lambda x: format_currency(x))
                daily_df['7-Day Rolling Avg'] = daily_df['7-Day Rolling Avg'].apply(lambda x: format_currency(x))
                st.dataframe(daily_df.sort_values('Date', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No data available for the selected date range.")
    
    # Monthly revenue chart
    with chart_tabs[1]:
        monthly_df = group_by_month(orders)
        
        if not monthly_df.empty:
            # Add month name for display
            monthly_df['Month Name'] = monthly_df['Month'].apply(
                lambda x: dt.strptime(x, '%Y-%m').strftime('%b %Y')
            )
            
            # Create figure
            fig = px.bar(
                monthly_df, 
                x='Month Name', 
                y='Total',
                title='Monthly Revenue',
                color='Total',
                color_continuous_scale='Reds'
            )
            fig.update_layout(
                xaxis_title='Month',
                yaxis_title='Revenue (£)',
                coloraxis_showscale=False,
                hovermode='x unified'
            )
            
            # Add currency to hover
            fig.update_traces(
                hovertemplate='%{y:£,.2f}'
            )
            
            # Format y-axis as currency
            fig.update_layout(
                yaxis=dict(
                    tickprefix='£',
                    separatethousands=True
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Calculate month-over-month growth
            st.subheader("Month-over-Month Growth")
            
            # Create a copy with month converted to datetime for easier sorting
            growth_df = monthly_df.copy()
            growth_df['Month Date'] = growth_df['Month'].apply(lambda x: dt.strptime(x, '%Y-%m'))
            growth_df = growth_df.sort_values('Month Date')
            
            # Calculate growth
            growth_df['Previous Month'] = growth_df['Total'].shift(1)
            growth_df['MoM Growth'] = (growth_df['Total'] - growth_df['Previous Month']) / growth_df['Previous Month'] * 100
            growth_df['MoM Growth'] = growth_df['MoM Growth'].fillna(0)
            
            # Display as a chart
            growth_fig = px.bar(
                growth_df,
                x='Month Name',
                y='MoM Growth',
                title='Month-over-Month Revenue Growth (%)',
                color='MoM Growth',
                color_continuous_scale='RdBu',
                color_continuous_midpoint=0
            )
            growth_fig.update_layout(
                xaxis_title='Month',
                yaxis_title='Growth (%)',
                coloraxis_showscale=False
            )
            
            # Add percentage to hover
            growth_fig.update_traces(
                hovertemplate='%{y:.1f}%'
            )
            
            st.plotly_chart(growth_fig, use_container_width=True)
        else:
            st.info("No data available for the selected date range.")
    
    # Menu analysis
    with chart_tabs[2]:
        menu_df = group_by_menu(filtered_orders)
        
        if not menu_df.empty:
            # Calculate menu share percentages
            total_revenue = menu_df['Total'].sum()
            menu_df['Percentage'] = (menu_df['Total'] / total_revenue * 100)
            
            # Create a pie chart for menu share
            fig_pie = px.pie(
                menu_df,
                values='Total',
                names='Menu',
                title='Revenue by Menu Type',
                color_discrete_sequence=px.colors.sequential.Reds
            )
            
            # Improve pie chart appearance
            fig_pie.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='%{label}<br>%{value:£,.2f}<br>%{percent}'
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Bar chart of menu revenue
            fig_bar = px.bar(
                menu_df,
                x='Menu',
                y='Total',
                title='Revenue by Menu Type',
                color='Total',
                color_continuous_scale='Reds'
            )
            fig_bar.update_layout(
                xaxis_title='Menu Type',
                yaxis_title='Revenue (£)',
                coloraxis_showscale=False
            )
            
            # Add currency to hover
            fig_bar.update_traces(
                hovertemplate='%{y:£,.2f}'
            )
            
            # Format y-axis as currency
            fig_bar.update_layout(
                yaxis=dict(
                    tickprefix='£',
                    separatethousands=True
                )
            )
            
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # Display menu revenue table
            with st.expander("Show Menu Revenue Table"):
                display_df = menu_df.copy()
                display_df['Total'] = display_df['Total'].apply(lambda x: format_currency(x))
                display_df['Percentage'] = display_df['Percentage'].apply(lambda x: f"{x:.1f}%")
                st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No data available for the selected date range.")
    
    # Payment methods analysis
    with chart_tabs[3]:
        payment_df = group_by_payment_method(filtered_orders)
        
        if not payment_df.empty:
            # Calculate payment method percentages
            total_revenue = payment_df['Total'].sum()
            payment_df['Percentage'] = (payment_df['Total'] / total_revenue * 100)
            
            # Create a pie chart for payment methods
            fig_pie = px.pie(
                payment_df,
                values='Total',
                names='Payment Method',
                title='Revenue by Payment Method',
                color_discrete_sequence=px.colors.sequential.Blues
            )
            
            # Improve pie chart appearance
            fig_pie.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='%{label}<br>%{value:£,.2f}<br>%{percent}'
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Display payment method table
            with st.expander("Show Payment Method Revenue Table"):
                display_df = payment_df.copy()
                display_df['Total'] = display_df['Total'].apply(lambda x: format_currency(x))
                display_df['Percentage'] = display_df['Percentage'].apply(lambda x: f"{x:.1f}%")
                st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No data available for the selected date range.")
    
    # Revenue forecast
    st.header("Revenue Forecast")
    
    # Only show forecast if we have enough data
    if date_filter in ["Last 90 days", "Year to date", "All time"]:
        # Group by date for trend analysis
        forecast_df = group_by_date(orders)
        
        if not forecast_df.empty and len(forecast_df) > 30:  # Need at least 30 data points
            # Simple moving average forecast
            forecast_period = 30  # days
            
            # Create a datetime index for continuous dates
            date_range = pd.date_range(
                start=forecast_df['Date'].min(),
                end=forecast_df['Date'].max()
            )
            
            # Reindex to fill in missing dates with 0
            forecast_df = forecast_df.set_index('Date')
            forecast_df = forecast_df.reindex(date_range, fill_value=0)
            forecast_df = forecast_df.reset_index()
            forecast_df = forecast_df.rename(columns={'index': 'Date'})
            
            # Calculate moving average
            forecast_df['MA_30'] = forecast_df['Total'].rolling(window=30, min_periods=1).mean()
            
            # Create a date range for the forecast period
            last_date = forecast_df['Date'].max()
            forecast_dates = pd.date_range(
                start=last_date + timedelta(days=1),
                periods=forecast_period
            )
            
            # Use the last 30-day average as forecast
            forecast_value = forecast_df['MA_30'].iloc[-1]
            
            # Create forecast dataframe
            forecast_data = pd.DataFrame({
                'Date': forecast_dates,
                'Forecast': [forecast_value] * forecast_period
            })
            
            # Combine historical and forecast data
            combined_df = pd.concat([
                forecast_df[['Date', 'Total']],
                forecast_data[['Date', 'Forecast']]
            ])
            
            # Create figure
            fig = go.Figure()
            
            # Add historical data
            fig.add_trace(go.Scatter(
                x=forecast_df['Date'],
                y=forecast_df['Total'],
                name='Actual Revenue',
                line=dict(color='#FF6B6B', width=2)
            ))
            
            # Add moving average
            fig.add_trace(go.Scatter(
                x=forecast_df['Date'],
                y=forecast_df['MA_30'],
                name='30-Day Average',
                line=dict(color='#4ECDC4', width=2)
            ))
            
            # Add forecast
            fig.add_trace(go.Scatter(
                x=forecast_data['Date'],
                y=forecast_data['Forecast'],
                name='Forecast',
                line=dict(color='#FFE66D', width=2, dash='dash')
            ))
            
            # Customize layout
            fig.update_layout(
                title='Revenue Forecast (Next 30 Days)',
                xaxis_title='Date',
                yaxis_title='Revenue (£)',
                hovermode='x unified',
                yaxis=dict(
                    tickprefix='£',
                    separatethousands=True
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Forecast summary
            st.metric(
                label="Forecasted Monthly Revenue", 
                value=format_currency(forecast_value * 30)
            )
            
            st.caption("Note: This is a simple forecast based on the 30-day moving average of historical data.")
        else:
            st.info("Not enough historical data available for forecasting.")
    else:
        st.info("Select a longer date range (at least 90 days) to view revenue forecasts.")
    
    # Export options
    st.header("Export Data")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Export to CSV"):
            # In a real app, you would generate and download a CSV file
            st.success("CSV export functionality would be implemented here.")
    
    with col2:
        if st.button("Export to Excel"):
            # In a real app, you would generate and download an Excel file
            st.success("Excel export functionality would be implemented here.")
