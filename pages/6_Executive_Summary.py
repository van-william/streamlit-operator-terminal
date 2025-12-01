import streamlit as st
import pandas as pd
from datetime import datetime, date
from db import (
    get_lines, get_operators, get_safety_incidents,
    get_production_summary, get_quality_summary, get_downtime_summary,
    create_action, get_actions, close_action, get_targets
)

st.set_page_config(page_title="Executive Summary Dashboard", layout="wide")
st.title("Executive Summary Dashboard (Tier 2)")

if hasattr(st, "page_link"):
    st.page_link("pages/5_Value_Stream_SQDC.py", label="Go to Value Stream Board", icon="📊")

# --- Date Context ---
selected_date = st.date_input("View Date", date.today())
start_ts = datetime.combine(selected_date, datetime.min.time()).isoformat()
end_ts = datetime.combine(selected_date, datetime.max.time()).isoformat()

# --- Gather Data ---
lines_df = get_lines()
if lines_df.empty:
    st.error("No lines configured.")
    st.stop()

# Helper to calculate metrics for a line
def calculate_metrics(line_id):
    # Fetch targets
    targets = get_targets(line_id)
    t_safety = targets.get("safety", 0.0)
    t_quality = targets.get("quality", 95.0)
    t_delivery = targets.get("delivery", 100.0)
    t_cost = targets.get("cost", 30.0)

    # Safety
    safety_df = get_safety_incidents(line_id, start_ts[:10], end_ts[:10])
    incidents = len(safety_df)
    
    # Quality
    q_df = get_quality_summary(start_ts, end_ts)
    q_df = q_df[q_df['line_id'] == line_id]
    scrap = q_df['quantity'].sum() if not q_df.empty else 0
    
    p_df = get_production_summary(start_ts, end_ts)
    p_df = p_df[p_df['line_id'] == line_id]
    good = p_df['good_quantity'].sum() if not p_df.empty else 0
    
    total = good + scrap
    fpy = (good / total * 100) if total > 0 else 100.0
    
    # Delivery
    delivery_pct = (good / t_delivery * 100) if t_delivery > 0 else 0
    
    # Cost
    dt_df = get_downtime_summary(start_ts, end_ts)
    dt_df = dt_df[dt_df['line_id'] == line_id]
    downtime = dt_df['duration_minutes'].sum() if not dt_df.empty else 0
    
    return {
        "safety": {"val": incidents, "ok": incidents <= t_safety},
        "quality": {"val": fpy, "ok": fpy >= t_quality},
        "delivery": {"val": good, "target": t_delivery, "ok": good >= t_delivery},
        "cost": {"val": downtime, "ok": downtime <= t_cost}
    }

metrics_map = {}
alerts = []

st.subheader("Plant-Wide Status Matrix")
# Header
cols = st.columns([2, 2, 2, 2, 2])
cols[0].markdown("**Value Stream**")
cols[1].markdown("**Safety**")
cols[2].markdown("**Quality**")
cols[3].markdown("**Delivery**")
cols[4].markdown("**Cost**")
st.divider()

for _, line in lines_df.iterrows():
    lid = line['id']
    lname = line['name']
    m = calculate_metrics(lid)
    metrics_map[lid] = m
    
    cols = st.columns([2, 2, 2, 2, 2])
    cols[0].write(f"**{lname}**")
    
    # Safety
    s_icon = "✅" if m['safety']['ok'] else "🔴"
    cols[1].write(f"{s_icon} {m['safety']['val']} Incidents")
    if not m['safety']['ok']: alerts.append(f"{lname}: Safety Incident Reported")
        
    # Quality
    q_icon = "✅" if m['quality']['ok'] else "🔴"
    cols[2].write(f"{q_icon} {m['quality']['val']:.1f}% FPY")
    if not m['quality']['ok']: alerts.append(f"{lname}: Quality FPY Below Target")
    
    # Delivery
    d_icon = "✅" if m['delivery']['ok'] else "🔴"
    cols[3].write(f"{d_icon} {m['delivery']['val']}/{m['delivery']['target']}")
    if not m['delivery']['ok']: alerts.append(f"{lname}: Delivery Target Missed")
    
    # Cost
    c_icon = "✅" if m['cost']['ok'] else "🔴"
    cols[4].write(f"{c_icon} {m['cost']['val']:.0f} min DT")
    if not m['cost']['ok']: alerts.append(f"{lname}: High Downtime")

st.divider()

# --- Alerts & Actions ---
col_alerts, col_actions = st.columns([1, 2])

with col_alerts:
    st.subheader("⚠️ Alerts")
    if alerts:
        for a in alerts:
            st.warning(a)
    else:
        st.success("All metrics on target.")

with col_actions:
    st.subheader("Create Action Item")
    with st.form("new_action"):
        c1, c2 = st.columns(2)
        with c1:
            line_choice = st.selectbox("Line", lines_df['name'])
            line_id_act = lines_df[lines_df['name'] == line_choice]['id'].values[0]
            cat_choice = st.selectbox("Category", ["Safety", "Quality", "Delivery", "Cost", "Other"])
        with c2:
            ops_df = get_operators()
            assignee = st.selectbox("Assign To", ops_df['name'] if not ops_df.empty else ["Unassigned"])
            assignee_id = ops_df[ops_df['name'] == assignee]['id'].values[0] if not ops_df.empty else None
        
        desc = st.text_area("Description")
        
        if st.form_submit_button("Create Action"):
            create_action(line_id_act, cat_choice, desc, assignee_id)
            st.success("Action Created!")
            st.rerun()

st.divider()

# --- Action List ---
st.subheader("Open Actions")
open_actions = get_actions(status="open")

if not open_actions.empty:
    for _, row in open_actions.iterrows():
        with st.expander(f"[{row['category']}] {row['line_name']} - {row['timestamp'][:10]} (Assigned: {row['assignee_name']})"):
            st.write(f"**Description:** {row['description']}")
            with st.form(f"close_action_{row['id']}"):
                notes = st.text_input("Resolution Notes")
                if st.form_submit_button("Close Action"):
                    close_action(row['id'], notes)
                    st.success("Action Closed.")
                    st.rerun()
else:
    st.info("No open actions.")

