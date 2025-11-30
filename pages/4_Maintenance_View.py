import streamlit as st
import pandas as pd
from datetime import datetime
import time
from db import (
    get_operators, get_active_maintenance_events, 
    acknowledge_downtime_event, resolve_downtime_event
)

st.set_page_config(page_title="Maintenance View", layout="wide")
st.title("Maintenance Technician View")

# --- 1. Technician Identity ---
st.sidebar.header("Technician Login")
operators_df = get_operators()
tech_options = {row["name"]: row["id"] for _, row in operators_df.iterrows()}

# Simple Select for MVP (Real app would have auth)
selected_tech_name = st.sidebar.selectbox(
    "Select Technician",
    options=list(tech_options.keys())
)
selected_tech_id = tech_options[selected_tech_name] if selected_tech_name else None

if not selected_tech_id:
    st.warning("Please select a technician to proceed.")
    st.stop()

st.write(f"**Logged in as:** {selected_tech_name}")

# --- 2. Active Calls Queue ---
st.subheader("Active Maintenance Calls")

# Auto-refresh for real-time feel
auto_refresh = st.toggle("Auto-refresh (5s)", value=True)

active_events = get_active_maintenance_events()

if active_events.empty:
    st.success("No active downtime events. All systems running!")
else:
    # Display cards for each event
    for _, row in active_events.iterrows():
        # Card Styling based on status
        is_acknowledged = pd.notnull(row['acknowledged_at'])
        status_color = "orange" if is_acknowledged else "red"
        status_text = "IN PROGRESS" if is_acknowledged else "OPEN"
        
        with st.container():
            st.markdown(f"""
            <div style="border: 2px solid {status_color}; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                <h3 style="color: {status_color}; margin: 0;">{status_text} - {row['line_name']} / {row['machine_name']}</h3>
                <p><strong>Reason:</strong> {row['reason_description']} ({row['reason_code']})</p>
                <p><strong>Started:</strong> {row['start_time']} ({(datetime.now() - datetime.fromisoformat(row['start_time'])).seconds // 60} min ago)</p>
                <p><strong>Operator:</strong> {row['operator_name'] or 'Unknown'}</p>
                <p><strong>Notes:</strong> {row['notes'] or 'None'}</p>
            </div>
            """, unsafe_allow_html=True)
            
            col_act1, col_act2 = st.columns([1, 4])
            
            with col_act1:
                if not is_acknowledged:
                    if st.button(f"Acknowledge #{row['id']}", key=f"ack_{row['id']}", type="primary"):
                        acknowledge_downtime_event(row['id'], selected_tech_id)
                        st.success(f"Acknowledged event #{row['id']}")
                        st.rerun()
                else:
                    st.write(f"**Tech:** {row['technician_name']}")
                    st.write(f"**Ack at:** {row['acknowledged_at']}")

            with col_act2:
                if is_acknowledged:
                    # Resolution Form
                    with st.expander("Resolve & Close", expanded=True):
                        res_notes = st.text_input("Resolution / Root Cause Notes", key=f"res_note_{row['id']}")
                        if st.button(f"Close Ticket #{row['id']}", key=f"close_{row['id']}", type="secondary"):
                            if res_notes:
                                resolve_downtime_event(row['id'], res_notes)
                                st.success(f"Closed event #{row['id']}")
                                st.rerun()
                            else:
                                st.error("Please enter resolution notes.")

            st.divider()


# Handle Auto-refresh at the end
if auto_refresh:
    time.sleep(5)
    st.rerun()
