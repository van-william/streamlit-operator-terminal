import streamlit as st
import pandas as pd
from datetime import datetime
import time
from db import (
    get_lines, get_machines, get_work_orders, get_operators,
    get_downtime_reasons, get_quality_reasons,
    create_downtime_event, close_downtime_event, get_active_downtime_event,
    log_quality_event, log_production_count,
    get_recent_downtime_events, get_recent_quality_events
)

st.set_page_config(page_title="Operator Panel", layout="wide")

st.title("Operator Panel")

# --- 1. Context Selection ---
st.sidebar.header("Context")

# Load Data
lines_df = get_lines()
operators_df = get_operators()
downtime_reasons_df = get_downtime_reasons()
quality_reasons_df = get_quality_reasons()

# Initialize session state for context if not present
if "selected_line_id" not in st.session_state:
    st.session_state.selected_line_id = None
if "selected_machine_id" not in st.session_state:
    st.session_state.selected_machine_id = None
if "selected_wo_id" not in st.session_state:
    st.session_state.selected_wo_id = None
if "selected_operator_id" not in st.session_state:
    st.session_state.selected_operator_id = None

# --- URL Params Handling ---
# Expecting params: ?line=LineName&machine=MachineName&wo=WONumber&operator=OperatorName
# Compatibility for older Streamlit versions
try:
    query_params = st.query_params
except AttributeError:
    query_params = st.experimental_get_query_params()

if query_params:
    # Helper to get first value from list or string
    def get_param(key):
        val = query_params.get(key)
        if not val:
            return None
        return val[0] if isinstance(val, list) else val

    # Line
    target_line = get_param("line")
    if target_line and not st.session_state.selected_line_id:
        # Find ID
        line_match = lines_df[lines_df['name'] == target_line]
        if not line_match.empty:
            st.session_state.selected_line_id = int(line_match.iloc[0]['id'])
            
    # Machine
    target_machine = get_param("machine")
    if target_machine and not st.session_state.selected_machine_id:
         if st.session_state.selected_line_id:
             machines_for_line = get_machines(st.session_state.selected_line_id)
             machine_match = machines_for_line[machines_for_line['name'] == target_machine]
             if not machine_match.empty:
                 st.session_state.selected_machine_id = int(machine_match.iloc[0]['id'])

    # Operator
    target_op = get_param("operator")
    if target_op and not st.session_state.selected_operator_id:
        op_match = operators_df[operators_df['name'] == target_op]
        if not op_match.empty:
             st.session_state.selected_operator_id = int(op_match.iloc[0]['id'])
    
    # Work Order
    target_wo = get_param("wo")
else:
    target_wo = None


# Line Selection
line_options = {row["name"]: row["id"] for _, row in lines_df.iterrows()}
# Determine default index
line_default_index = 0
if st.session_state.selected_line_id:
    # Find name for ID
    current_name = next((k for k, v in line_options.items() if v == st.session_state.selected_line_id), None)
    if current_name:
        line_keys = list(line_options.keys())
        if current_name in line_keys:
            line_default_index = line_keys.index(current_name)

selected_line_name = st.sidebar.selectbox(
    "Select Line",
    options=list(line_options.keys()),
    index=line_default_index if line_options else None
)
if selected_line_name:
    st.session_state.selected_line_id = line_options[selected_line_name]

# Machine Selection (Filtered by Line)
machines_df = pd.DataFrame()
if st.session_state.selected_line_id:
    machines_df = get_machines(st.session_state.selected_line_id)

machine_options = {}
machine_default_index = 0
if not machines_df.empty:
    machine_options = {row["name"]: row["id"] for _, row in machines_df.iterrows()}
    
    if st.session_state.selected_machine_id:
        current_m_name = next((k for k, v in machine_options.items() if v == st.session_state.selected_machine_id), None)
        if current_m_name:
            m_keys = list(machine_options.keys())
            if current_m_name in m_keys:
                machine_default_index = m_keys.index(current_m_name)

selected_machine_name = st.sidebar.selectbox(
    "Select Machine",
    options=list(machine_options.keys()),
    index=machine_default_index if machine_options else None
)
if selected_machine_name:
    st.session_state.selected_machine_id = machine_options[selected_machine_name]
else:
    st.session_state.selected_machine_id = None

# Work Order Selection (Filtered by Line)
wo_df = pd.DataFrame()
if st.session_state.selected_line_id:
    wo_df = get_work_orders(st.session_state.selected_line_id)

wo_options = {}
wo_default_index = 0

if not wo_df.empty:
    wo_options = {row["wo_number"]: row["id"] for _, row in wo_df.iterrows()}
    
    # Check URL param for WO here if not set
    if target_wo and not st.session_state.selected_wo_id:
         if target_wo in wo_options:
             st.session_state.selected_wo_id = wo_options[target_wo]

    if st.session_state.selected_wo_id:
        current_wo = next((k for k, v in wo_options.items() if v == st.session_state.selected_wo_id), None)
        if current_wo:
            w_keys = list(wo_options.keys())
            if current_wo in w_keys:
                wo_default_index = w_keys.index(current_wo)

selected_wo_number = st.sidebar.selectbox(
    "Select Work Order",
    options=list(wo_options.keys()),
    index=wo_default_index if wo_options else None
)
if selected_wo_number:
    st.session_state.selected_wo_id = wo_options[selected_wo_number]
else:
    st.session_state.selected_wo_id = None

# Operator Selection
operator_options = {row["name"]: row["id"] for _, row in operators_df.iterrows()}
op_default_index = 0
if st.session_state.selected_operator_id:
    current_op = next((k for k, v in operator_options.items() if v == st.session_state.selected_operator_id), None)
    if current_op:
        o_keys = list(operator_options.keys())
        if current_op in o_keys:
            op_default_index = o_keys.index(current_op)

selected_operator_name = st.sidebar.selectbox(
    "Select Operator",
    options=list(operator_options.keys()),
    index=op_default_index if operator_options else None
)
if selected_operator_name:
    st.session_state.selected_operator_id = operator_options[selected_operator_name]


# Verify Context
if not st.session_state.selected_machine_id:
    st.warning("Please select a Machine to proceed.")
    st.stop()

# --- 2. Current Status / Downtime Timer ---
st.subheader("Machine Status")

# Check for active downtime
active_downtime = get_active_downtime_event(st.session_state.selected_machine_id)
active_downtime_id = active_downtime["id"] if active_downtime else None

col1, col2 = st.columns(2)

if active_downtime_id:
    # DOWN STATE
    with col1:
        st.error(f"DOWN - {selected_machine_name}")
        st.write(f"**Started:** {active_downtime['start_time']}")
        
        # Calculate elapsed time
        start_dt = datetime.fromisoformat(active_downtime["start_time"])
        elapsed = datetime.now() - start_dt
        st.metric("Elapsed Time", str(elapsed).split('.')[0]) # HH:MM:SS
        
        # Display Reason
        reason_row = downtime_reasons_df[downtime_reasons_df["id"] == active_downtime["reason_id"]].iloc[0]
        st.write(f"**Reason:** {reason_row['description']} ({reason_row['code']})")
        
        if st.button("End Downtime", type="primary", use_container_width=True):
            close_downtime_event(active_downtime_id)
            st.success("Downtime ended.")
            st.rerun()
        
        # Auto-refresh mechanism for timer
        time.sleep(5)
        st.rerun()

else:
    # RUNNING STATE
    with col1:
        st.success(f"RUNNING - {selected_machine_name}")
        
        st.write("### Start Downtime")
        
        # Reason Selector for new downtime
        reason_map = {f"{row['code']} - {row['description']}": row['id'] for _, row in downtime_reasons_df.iterrows()}
        selected_reason_str = st.selectbox("Select Downtime Reason", options=list(reason_map.keys()))
        selected_reason_id = reason_map[selected_reason_str]
        
        downtime_notes = st.text_input("Notes (Optional)")
        
        if st.button("Start Downtime", type="primary", use_container_width=True):
            create_downtime_event(
                st.session_state.selected_machine_id,
                st.session_state.selected_line_id,
                st.session_state.selected_wo_id,
                st.session_state.selected_operator_id,
                selected_reason_id,
                downtime_notes
            )
            st.rerun()

# --- 3. Quality / Scrap Logging ---
with col2:
    st.subheader("Log Production / Quality")
    
    if active_downtime_id:
        st.warning("Production logging is disabled while machine is DOWN.")
    else:
        tab1, tab2 = st.tabs(["Log Scrap", "Log Good Production"])
        
        with tab1:
            with st.form("scrap_form"):
                scrap_qty = st.number_input("Scrap Quantity", min_value=1, value=1)
                
                q_reason_map = {f"{row['code']} - {row['description']}": row['id'] for _, row in quality_reasons_df.iterrows()}
                selected_q_reason_str = st.selectbox("Reason", options=list(q_reason_map.keys()))
                selected_q_reason_id = q_reason_map[selected_q_reason_str]
                
                q_notes = st.text_input("Notes", key="q_notes")
                
                if st.form_submit_button("Log Scrap"):
                    log_quality_event(
                        st.session_state.selected_machine_id,
                        st.session_state.selected_line_id,
                        st.session_state.selected_wo_id,
                        st.session_state.selected_operator_id,
                        selected_q_reason_id,
                        scrap_qty,
                        q_notes
                    )
                    st.success("Scrap logged.")
                    st.rerun()

        with tab2:
            with st.form("good_prod_form"):
                good_qty = st.number_input("Good Quantity", min_value=1, value=1)
                
                if st.form_submit_button("Log Good Production"):
                    log_production_count(
                        st.session_state.selected_machine_id,
                        st.session_state.selected_line_id,
                        st.session_state.selected_wo_id,
                        st.session_state.selected_operator_id,
                        good_qty
                    )
                    st.success("Production logged.")
                    st.rerun()


# --- 4. Recent Events ---
st.divider()
st.subheader("Recent Activity")

col_recent_dt, col_recent_q = st.columns(2)

with col_recent_dt:
    st.write("#### Recent Downtime")
    recent_dt = get_recent_downtime_events(machine_id=st.session_state.selected_machine_id)
    if not recent_dt.empty:
        # Format for display
        display_dt = recent_dt[["start_time", "duration_minutes", "reason_description", "operator_name"]].copy()
        display_dt["duration_minutes"] = display_dt["duration_minutes"].round(1)
        st.dataframe(display_dt, hide_index=True)
    else:
        st.info("No recent downtime.")

with col_recent_q:
    st.write("#### Recent Quality Issues")
    recent_q = get_recent_quality_events(machine_id=st.session_state.selected_machine_id)
    if not recent_q.empty:
         # Format for display
        display_q = recent_q[["timestamp", "quantity", "reason_description"]].copy()
        st.dataframe(display_q, hide_index=True)
    else:
        st.info("No recent quality issues.")
