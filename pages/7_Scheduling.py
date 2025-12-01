import streamlit as st
import pandas as pd
import time
from datetime import datetime
from db import (
    get_work_orders, create_work_order, update_work_order_status,
    get_lines
)

st.set_page_config(page_title="Scheduling", layout="wide")
st.title("Production Scheduling")

# --- Tabs ---
tab_view, tab_add = st.tabs(["View Schedule", "Add Work Order"])

# --- Tab 1: View Schedule ---
with tab_view:
    st.subheader("Current Schedule")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        line_filter = st.selectbox("Filter by Line", ["All"] + list(get_lines()["name"]), index=0)
    with col2:
        status_filter = st.selectbox("Filter by Status", ["All", "Scheduled", "Active", "Completed"], index=0)
        
    # Data Loading
    lines_df = get_lines()
    line_id = None
    if line_filter != "All":
        line_id = lines_df[lines_df["name"] == line_filter].iloc[0]["id"]
        
    status = None if status_filter == "All" else status_filter
    
    wo_df = get_work_orders(line_id=line_id, status=status)
    
    if not wo_df.empty:
        # Enrich with line names if needed (lines already linked via foreign key, but we have line_id in df)
        # Let's merge for better display
        display_df = wo_df.merge(lines_df, left_on="line_id", right_on="id", suffixes=("", "_line"))
        
        # Display as a table with actions
        for index, row in display_df.iterrows():
            with st.expander(f"{row['wo_number']} - {row['part_number']} ({row['status']})"):
                c1, c2, c3, c4 = st.columns(4)
                c1.write(f"**Target:** {row['target_quantity']}")
                c2.write(f"**Line:** {row['name']}")
                c3.write(f"**Due:** {row['due_date']}")
                
                # Actions
                current_status = row['status']
                if current_status == "Scheduled":
                    if c4.button("Start Order", key=f"start_{row['id']}"):
                        update_work_order_status(row['id'], "Active")
                        st.success(f"Started {row['wo_number']}")
                        st.rerun()
                elif current_status == "Active":
                    if c4.button("Complete Order", key=f"complete_{row['id']}"):
                        update_work_order_status(row['id'], "Completed")
                        st.success(f"Completed {row['wo_number']}")
                        st.rerun()
                elif current_status == "Completed":
                    c4.write(f"Completed on: {row['completed_date']}")
    else:
        st.info("No work orders found matching filters.")

# --- Tab 2: Add Work Order ---
with tab_add:
    st.subheader("Create New Work Order")
    
    with st.form("new_wo_form"):
        col1, col2 = st.columns(2)
        with col1:
            wo_number = st.text_input("WO Number (e.g. WO-2024-001)")
            part_number = st.text_input("Part Number")
            target_qty = st.number_input("Target Quantity", min_value=1, value=100)
        
        with col2:
            lines_df = get_lines()
            line_options = {row["name"]: row["id"] for _, row in lines_df.iterrows()}
            selected_line_name = st.selectbox("Line", list(line_options.keys()))
            due_date = st.date_input("Due Date")
            
        submit = st.form_submit_button("Create Work Order")
        
        if submit:
            if wo_number and part_number:
                create_work_order(
                    wo_number, 
                    part_number, 
                    target_qty, 
                    due_date.isoformat(), 
                    line_options[selected_line_name]
                )
                st.success(f"Work Order {wo_number} created!")
                time.sleep(1) # wait a bit
                st.rerun()
            else:
                st.error("Please fill in all required fields.")

