import streamlit as st
import pandas as pd
from db import (
    get_lines, get_machines, get_operators, get_downtime_reasons,
    add_line, add_machine, add_operator, add_downtime_reason
)

st.set_page_config(page_title="Admin Config", layout="wide")
st.title("Admin Configuration")

tab_lines, tab_machines, tab_operators, tab_reasons = st.tabs([
    "Lines", "Machines", "Operators", "Downtime Reasons"
])

# --- Lines ---
with tab_lines:
    st.subheader("Lines")
    lines_df = get_lines()
    st.dataframe(lines_df, hide_index=True)
    
    with st.expander("Add New Line"):
        with st.form("add_line_form"):
            name = st.text_input("Line Name")
            desc = st.text_input("Description")
            if st.form_submit_button("Add Line"):
                if name:
                    add_line(name, desc)
                    st.success(f"Added line: {name}")
                    st.rerun()
                else:
                    st.error("Name is required.")

# --- Machines ---
with tab_machines:
    st.subheader("Machines")
    machines_df = get_machines()
    
    # Merge with Line Names for display
    if not machines_df.empty and not lines_df.empty:
        display_machines = pd.merge(
            machines_df, 
            lines_df[['id', 'name']].rename(columns={'id': 'line_id', 'name': 'line_name'}), 
            on='line_id', 
            how='left'
        )
    else:
        display_machines = machines_df
        
    st.dataframe(display_machines, hide_index=True)
    
    with st.expander("Add New Machine"):
        with st.form("add_machine_form"):
            m_name = st.text_input("Machine Name")
            
            line_options = {row["name"]: row["id"] for _, row in lines_df.iterrows()}
            selected_line = st.selectbox("Line", options=list(line_options.keys()))
            
            m_desc = st.text_input("Description")
            
            if st.form_submit_button("Add Machine"):
                if m_name and selected_line:
                    add_machine(m_name, line_options[selected_line], m_desc)
                    st.success(f"Added machine: {m_name}")
                    st.rerun()
                else:
                    st.error("Name and Line are required.")

# --- Operators ---
with tab_operators:
    st.subheader("Operators")
    operators_df = get_operators()
    st.dataframe(operators_df, hide_index=True)
    
    with st.expander("Add New Operator"):
        with st.form("add_op_form"):
            op_name = st.text_input("Operator Name")
            badge = st.text_input("Badge ID")
            if st.form_submit_button("Add Operator"):
                if op_name:
                    add_operator(op_name, badge)
                    st.success(f"Added operator: {op_name}")
                    st.rerun()
                else:
                    st.error("Name is required.")

# --- Downtime Reasons ---
with tab_reasons:
    st.subheader("Downtime Reasons")
    reasons_df = get_downtime_reasons()
    st.dataframe(reasons_df, hide_index=True)
    
    with st.expander("Add New Reason"):
        with st.form("add_reason_form"):
            code = st.text_input("Reason Code (e.g. MECH)")
            desc = st.text_input("Description")
            category = st.selectbox("Category", ["Unplanned", "Planned"])
            
            if st.form_submit_button("Add Reason"):
                if code and desc:
                    add_downtime_reason(code, desc, category)
                    st.success(f"Added reason: {code}")
                    st.rerun()
                else:
                    st.error("Code and Description are required.")

