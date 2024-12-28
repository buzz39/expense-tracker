import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import calendar
from notion_client import Client
import os
from datetime import datetime
import logging
from datetime import timezone

# Set up logging at the start of the file, after imports
logging.basicConfig(
    filename='expense_tracker.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Set page config
st.set_page_config(page_title="Expense Tracker", layout="wide")

# Notion API Configuration
@st.cache_resource
def get_notion_client():
    # Get Notion API key from environment variable or Streamlit secrets
    notion_token = st.secrets["NOTION_TOKEN"]
    return Client(auth=notion_token)

@st.cache_data(ttl=300)
def load_data_from_notion():
    try:
        notion = get_notion_client()
        database_id = st.secrets["NOTION_DATABASE_ID"]
        
        # Query the database
        results = []
        query = notion.databases.query(database_id=database_id)
        
        logging.info(f"Retrieved {len(query['results'])} initial results from Notion")
        
        # Debug: Log the first result structure
        if query["results"]:
            logging.debug(f"First result structure: {query['results'][0]['properties']}")
        
        results.extend(query["results"])
        
        # Handle pagination
        while query.get("has_more", False):
            query = notion.databases.query(
                database_id=database_id,
                start_cursor=query["next_cursor"]
            )
            results.extend(query["results"])
            logging.info(f"Retrieved additional {len(query['results'])} results")
        
        processed_data = []
        for page in results:
            try:
                properties = page["properties"]
                date_value = properties.get("Date", {}).get("date", {}).get("start")
                
                # Debug category extraction
                category_prop = properties.get("Category", {})
                logging.info(f"Category property: {category_prop}")
                
                # Handle different possible category field types in Notion
                category_value = ""
                if category_prop:
                    if "select" in category_prop:
                        category_value = category_prop["select"]["name"] if category_prop["select"] else ""
                    elif "multi_select" in category_prop:
                        multi_select = category_prop["multi_select"]
                        category_value = multi_select[0]["name"] if multi_select else ""
                    elif "rich_text" in category_prop:
                        rich_text = category_prop["rich_text"]
                        category_value = rich_text[0]["text"]["content"] if rich_text else ""
                    logging.info(f"Extracted category: {category_value}")
                
                # Handle different date formats and make timezone-aware
                if date_value:
                    try:
                        # Parse datetime and make it timezone-aware
                        parsed_date = pd.to_datetime(date_value, format='mixed')
                        if parsed_date.tzinfo is None:
                            parsed_date = parsed_date.tz_localize('UTC')
                        # Convert to local timezone (IST)
                        parsed_date = parsed_date.tz_convert('Asia/Kolkata')
                        # Make timezone-naive for consistent comparison
                        parsed_date = parsed_date.tz_localize(None)
                    except Exception as e:
                        logging.warning(f"Date parsing error: {e} for date {date_value}")
                        # If parsing fails, try date-only format
                        parsed_date = pd.to_datetime(date_value.split('T')[0])
                else:
                    parsed_date = None
                
                row = {
                    "Name": properties.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "") if properties.get("Name", {}).get("title") else "",
                    "Amount": float(properties.get("Amount", {}).get("number", 0) or 0),
                    "Category": category_value,  # Use the extracted category
                    "Date": parsed_date,
                    "Comment": properties.get("Comment", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "") if properties.get("Comment", {}).get("rich_text") else ""
                }
                processed_data.append(row)
            except Exception as e:
                logging.error(f"Error processing row: {e}")
                logging.error(f"Problematic row data: {properties}")
        
        if not processed_data:
            logging.error("No data could be processed from the Notion database")
            return pd.DataFrame(columns=['Name', 'Amount', 'Category', 'Date', 'Comment'])
        
        df = pd.DataFrame(processed_data)
        df = df.dropna(subset=['Date'])
        
        logging.info(f"Successfully processed {len(df)} rows of data")
        return df.sort_values('Date')
        
    except Exception as e:
        logging.error(f"Error in load_data_from_notion: {str(e)}")
        raise

# Modify the data loading section
try:
    data = load_data_from_notion()
    st.sidebar.success("✅ Connected to Notion database")
    logging.info("Successfully loaded data from Notion")
    
except Exception as e:
    error_msg = f"Error connecting to Notion: {str(e)}"
    logging.error(error_msg)
    st.error(error_msg)
    st.stop()

# Check if we have data
if data.empty:
    st.error("No data available")
    st.stop()

# Sidebar filters
st.sidebar.header("Filters")

# Date range filter
date_range = st.sidebar.date_input(
    "Select Date Range",
    [data['Date'].min(), data['Date'].max()],
    min_value=data['Date'].min(),
    max_value=data['Date'].max()
)

# Convert to datetime for filtering
if len(date_range) == 2:
    start_date, end_date = date_range
    mask = (data['Date'].dt.date >= start_date) & (data['Date'].dt.date <= end_date)
    filtered_data = data.loc[mask]
else:
    filtered_data = data

# Category filter
all_categories = sorted(data['Category'].unique())
selected_categories = st.sidebar.multiselect(
    "Select Categories",
    all_categories,
    default=all_categories
)

# Apply category filter
filtered_data = filtered_data[filtered_data['Category'].isin(selected_categories)]

# Main content
st.title("💰 Expense Analytics Dashboard")

# Top metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_expense = filtered_data['Amount'].sum()
    st.metric("Total Expenses", f"₹{total_expense:,.2f}")

with col2:
    avg_daily_expense = total_expense / len(filtered_data['Date'].dt.date.unique())
    st.metric("Average Daily Expense", f"₹{avg_daily_expense:,.2f}")

with col3:
    max_expense = filtered_data['Amount'].max()
    max_expense_name = filtered_data.loc[filtered_data['Amount'].idxmax(), 'Name']
    st.metric("Highest Expense", f"₹{max_expense:,.2f}", max_expense_name)

with col4:
    num_transactions = len(filtered_data)
    st.metric("Number of Transactions", num_transactions)

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("Daily Expenses Trend")
    daily_expenses = filtered_data.groupby('Date')['Amount'].sum().reset_index()
    fig = px.line(daily_expenses, x='Date', y='Amount',
                  labels={'Amount': 'Total Expense (₹)', 'Date': 'Date'},
                  line_shape='linear')
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Category-wise Distribution")
    category_expenses = filtered_data.groupby('Category')['Amount'].sum().reset_index()
    fig = px.pie(category_expenses, values='Amount', names='Category',
                 hole=0.4)
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

# Category-wise analysis
st.subheader("Category-wise Analysis")
col1, col2 = st.columns(2)

with col1:
    category_summary = filtered_data.groupby('Category').agg({
        'Amount': ['sum', 'mean', 'count']
    }).round(2)
    category_summary.columns = ['Total', 'Average', 'Count']
    category_summary = category_summary.sort_values('Total', ascending=False)
    
    # Format the currency columns
    category_summary['Total'] = category_summary['Total'].apply(lambda x: f"₹{x:,.2f}")
    category_summary['Average'] = category_summary['Average'].apply(lambda x: f"₹{x:,.2f}")
    
    st.dataframe(category_summary, use_container_width=True)

with col2:
    # Bar chart for category-wise expenses
    fig = px.bar(category_summary.reset_index(), x='Category', y='Total',
                 title="Category-wise Total Expenses",
                 labels={'Total': 'Total Expense (₹)'})
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

# Monthly Category Trends
st.subheader("Monthly Category Trends")

# Prepare monthly category data
filtered_data['Month'] = filtered_data['Date'].dt.strftime('%Y-%m')
monthly_category_data = filtered_data.pivot_table(
    index='Month',
    columns='Category',
    values='Amount',
    aggfunc='sum'
).fillna(0)

# Category selector for the trend
selected_categories_trend = st.multiselect(
    "Select Categories to Compare",
    all_categories,
    default=all_categories[:3],  # Default to first 3 categories
    key="trend_categories"  # Unique key to distinguish from sidebar multiselect
)

# Create the trend line chart
if selected_categories_trend:
    fig = go.Figure()
    
    for category in selected_categories_trend:
        fig.add_trace(go.Scatter(
            x=monthly_category_data.index,
            y=monthly_category_data[category],
            name=category,
            mode='lines+markers'
        ))
    
    fig.update_layout(
        title="Monthly Spending Trends by Category",
        xaxis_title="Month",
        yaxis_title="Total Expense (₹)",
        height=500,
        hovermode='x unified',
        yaxis=dict(tickformat="₹,.0f")
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show the monthly data in a table
    st.subheader("Monthly Category-wise Expenses")
    monthly_data_display = monthly_category_data[selected_categories_trend].copy()
    # Format all numbers as currency
    for col in monthly_data_display.columns:
        monthly_data_display[col] = monthly_data_display[col].apply(lambda x: f"₹{x:,.2f}")
    st.dataframe(monthly_data_display, use_container_width=True)

# Recent transactions
st.subheader("Recent Transactions")
recent_transactions = filtered_data.sort_values('Date', ascending=False).head(10)
st.dataframe(
    recent_transactions[['Date', 'Name', 'Amount', 'Category']].style.format({
        'Amount': lambda x: f"₹{x:,.2f}"
    }),
    use_container_width=True
)

# Download filtered data
st.download_button(
    label="Download Filtered Data",
    data=filtered_data.to_csv(index=False).encode('utf-8'),
    file_name="filtered_expenses.csv",
    mime="text/csv"
)