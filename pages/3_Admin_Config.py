import streamlit as st
import pandas as pd
from db import (
    get_lines, get_machines, get_operators, get_downtime_reasons,
    add_line, add_machine, add_operator, add_downtime_reason,
    set_target, get_targets
)

st.set_page_config(page_title="Admin Config", layout="wide")
st.title("Admin Configuration")

tab_lines, tab_machines, tab_operators, tab_reasons, tab_targets = st.tabs([
    "Lines", "Machines", "Operators", "Downtime Reasons", "SQDC Targets"
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

# --- SQDC Targets ---
with tab_targets:
    st.subheader("SQDC Targets Configuration")
    st.write("Set daily targets for each value stream. These targets drive the Red/Green status on the dashboards.")
    
    lines_df = get_lines()
    if not lines_df.empty:
        selected_line_name = st.selectbox("Select Line to Configure", lines_df["name"], key="target_line_select")
        selected_line_id = lines_df[lines_df["name"] == selected_line_name]["id"].values[0]
        
        # Load existing targets
        current_targets = get_targets(selected_line_id)
        
        # Defaults
        default_safety = current_targets.get("safety", 0.0)
        default_quality = current_targets.get("quality", 95.0)
        default_delivery = current_targets.get("delivery", 100.0)
        default_cost = current_targets.get("cost", 30.0)
        
        with st.form("targets_form"):
            col1, col2 = st.columns(2)
            with col1:
                t_safety = st.number_input("Safety Target (Max Incidents)", min_value=0.0, value=float(default_safety), step=1.0)
                st.caption("Goal is usually 0. Status is Red if > Target.")
                
                t_delivery = st.number_input("Delivery Target (Units/Day)", min_value=0.0, value=float(default_delivery), step=1.0)
                st.caption("Status is Green if Production >= Target.")

            with col2:
                t_quality = st.number_input("Quality Target (Min FPY %)", min_value=0.0, max_value=100.0, value=float(default_quality), step=0.1)
                st.caption("Status is Green if FPY % >= Target.")

                t_cost = st.number_input("Cost Target (Max Downtime Mins)", min_value=0.0, value=float(default_cost), step=5.0)
                st.caption("Status is Green if Downtime <= Target.")
            
            if st.form_submit_button("Save Targets"):
                set_target(selected_line_id, "safety", t_safety)
                set_target(selected_line_id, "quality", t_quality)
                set_target(selected_line_id, "delivery", t_delivery)
                set_target(selected_line_id, "cost", t_cost)
                st.success(f"Targets saved for {selected_line_name}!")
                st.rerun()
    else:
        st.info("No lines available. Please create a line first.")
