import streamlit as st
import pandas as pd
from datetime import datetime
from db import (
    get_lines, get_work_orders, get_operators,
    create_inspection_record, get_inspection_records,
    create_mrb_item, get_mrb_items, update_mrb_disposition
)

st.set_page_config(page_title="Quality Management", layout="wide")
st.title("Quality Management System")

# --- Tabs ---
tab_inspect, tab_mrb, tab_history = st.tabs(["Inspection Log", "Material Review Board (MRB)", "History & Reports"])

# --- Tab 1: Inspection Log ---
with tab_inspect:
    st.subheader("Log Inspection")
    
    col1, col2 = st.columns(2)
    with col1:
        # Context Selection
        lines_df = get_lines()
        line_options = {row["name"]: row["id"] for _, row in lines_df.iterrows()}
        selected_line_name = st.selectbox("Line", list(line_options.keys()), key="inspect_line")
        selected_line_id = line_options[selected_line_name] if selected_line_name else None
        
        wo_df = pd.DataFrame()
        if selected_line_id:
            wo_df = get_work_orders(selected_line_id, status="Active")
        
        wo_options = {f"{row['wo_number']} ({row['part_number']})": row["id"] for _, row in wo_df.iterrows()}
        selected_wo_label = st.selectbox("Active Work Order", list(wo_options.keys()), key="inspect_wo")
        selected_wo_id = wo_options[selected_wo_label] if selected_wo_label else None

        operators_df = get_operators()
        op_options = {row["name"]: row["id"] for _, row in operators_df.iterrows()}
        selected_op_name = st.selectbox("Inspector", list(op_options.keys()), key="inspect_op")
        selected_op_id = op_options[selected_op_name] if selected_op_name else None

    with col2:
        with st.form("inspection_form"):
            result = st.radio("Result", ["Pass", "Fail"], horizontal=True)
            measurements = st.text_area("Measurements / Data")
            notes = st.text_input("Notes")
            
            submit_inspect = st.form_submit_button("Submit Inspection")
            
            if submit_inspect:
                if selected_wo_id and selected_op_id:
                    create_inspection_record(
                        selected_wo_id,
                        selected_line_id,
                        selected_op_id,
                        result,
                        measurements,
                        notes
                    )
                    st.success("Inspection logged.")
                    if result == "Fail":
                        st.warning("Inspection Failed. Consider creating an MRB item.")
                else:
                    st.error("Please select Work Order and Inspector.")

# --- Tab 2: MRB ---
with tab_mrb:
    st.subheader("Material Review Board")
    
    mrb_action = st.radio("Action", ["View Open Items", "New MRB Item"], horizontal=True)
    
    if mrb_action == "New MRB Item":
        with st.form("new_mrb"):
            part_num = st.text_input("Part Number")
            qty = st.number_input("Quantity", min_value=1, value=1)
            reason = st.text_input("Reason for Quarantine")
            mrb_notes = st.text_area("Notes")
            
            if st.form_submit_button("Create MRB Ticket"):
                create_mrb_item(part_num, qty, reason, mrb_notes)
                st.success("Item added to MRB.")
                
    else:
        # View Open Items
        open_items = get_mrb_items(status="Open")
        if not open_items.empty:
            for _, row in open_items.iterrows():
                with st.expander(f"MRB #{row['id']} - {row['part_number']} (Qty: {row['quantity']})"):
                    c1, c2 = st.columns(2)
                    c1.write(f"**Reason:** {row['reason']}")
                    c1.write(f"**Created:** {row['created_at']}")
                    c1.write(f"**Notes:** {row['notes']}")
                    
                    with c2:
                        with st.form(f"disposition_{row['id']}"):
                            disposition = st.selectbox("Disposition", ["Scrap", "Rework", "Return to Vendor", "Use As Is"])
                            disp_notes = st.text_input("Disposition Notes")
                            if st.form_submit_button("Close Ticket"):
                                update_mrb_disposition(row['id'], disposition, disp_notes)
                                st.success("Ticket closed.")
                                st.rerun()
        else:
            st.info("No open MRB items.")

# --- Tab 3: History ---
with tab_history:
    st.subheader("Inspection History")
    # Show last 50 inspections
    recent_inspections = get_inspection_records()
    if not recent_inspections.empty:
        st.dataframe(recent_inspections)
    else:
        st.info("No inspection records found.")

    st.divider()
    st.subheader("MRB History")
    all_mrb = get_mrb_items()
    if not all_mrb.empty:
        st.dataframe(all_mrb)
    else:
        st.info("No MRB records found.")

