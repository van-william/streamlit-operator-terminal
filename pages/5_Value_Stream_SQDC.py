import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from db import (
    get_lines, get_safety_incidents, log_safety_incident,
    get_production_summary, get_quality_summary, get_downtime_summary,
    get_targets
)

st.set_page_config(page_title="Value Stream SQDC Board", layout="wide")

st.title("Value Stream SQDC Board")

if hasattr(st, "page_link"):
    st.page_link("pages/6_Executive_Summary.py", label="Go to Executive Summary", icon="📈")

# --- Filters ---
col1, col2 = st.columns(2)

with col1:
    lines_df = get_lines()
    if not lines_df.empty:
        selected_line_name = st.selectbox("Select Line", lines_df["name"])
        selected_line_id = lines_df[lines_df["name"] == selected_line_name]["id"].values[0]
    else:
        st.error("No lines found in database.")
        st.stop()

with col2:
    view_scope = st.radio("View Scope", ["Today", "This Week"], horizontal=True)
    if view_scope == "Today":
        selected_date = st.date_input("Date", date.today())
        start_ts = datetime.combine(selected_date, datetime.min.time()).isoformat()
        end_ts = datetime.combine(selected_date, datetime.max.time()).isoformat()
        period_days = 1
    else:
        # Week to date (starting Monday) or last 7 days. Let's do last 7 days including today.
        today = date.today()
        start_date = today - timedelta(days=6)
        st.write(f"Showing data from {start_date} to {today}")
        start_ts = datetime.combine(start_date, datetime.min.time()).isoformat()
        end_ts = datetime.combine(today, datetime.max.time()).isoformat()
        period_days = 7

# --- Metrics Calculation ---

# Get Targets
targets = get_targets(selected_line_id)
t_safety = targets.get("safety", 0.0)
t_quality = targets.get("quality", 95.0)
t_delivery = targets.get("delivery", 100.0)
t_cost = targets.get("cost", 30.0)

# 1. Safety
safety_df = get_safety_incidents(selected_line_id, start_ts[:10], end_ts[:10])
safety_incidents_count = len(safety_df)
# Safety is green if <= target (usually 0)
safety_status = "green" if safety_incidents_count <= t_safety else "red"

# 2. Quality
quality_df = get_quality_summary(start_ts, end_ts)
# Filter for line
quality_df = quality_df[quality_df['line_id'] == selected_line_id]
total_scrap = quality_df['quantity'].sum() if not quality_df.empty else 0

prod_df = get_production_summary(start_ts, end_ts)
prod_df = prod_df[prod_df['line_id'] == selected_line_id]
total_good = prod_df['good_quantity'].sum() if not prod_df.empty else 0

total_produced = total_good + total_scrap
fpy = (total_good / total_produced * 100) if total_produced > 0 else 100.0
quality_status = "green" if fpy >= t_quality else "red"

# 3. Delivery
# Target scales with period (e.g. weekly target = daily * 7)
period_target = t_delivery * period_days
delivery_status = "green" if total_good >= period_target else "red"

# 4. Cost (Downtime)
dt_df = get_downtime_summary(start_ts, end_ts)
dt_df = dt_df[dt_df['line_id'] == selected_line_id]
total_downtime_min = dt_df['duration_minutes'].sum() if not dt_df.empty else 0
# Target also scales with period? Usually we think of downtime per day.
period_downtime_target = t_cost * period_days
cost_status = "green" if total_downtime_min <= period_downtime_target else "red"


# --- Visual Board ---
st.divider()

c1, c2, c3, c4 = st.columns(4)

def status_indicator(status):
    return "✅" if status == "green" else "❌"

def status_color_box(status, text):
    if status == "green":
        st.success(text)
    else:
        st.error(text)

with c1:
    st.subheader("Safety")
    st.markdown(f"# {status_indicator(safety_status)}")
    status_color_box(safety_status, f"{safety_incidents_count} Incidents")
    st.caption(f"Target: ≤ {int(t_safety)}")
    if safety_incidents_count > t_safety:
        st.warning("Action required!")

with c2:
    st.subheader("Quality")
    st.markdown(f"# {status_indicator(quality_status)}")
    status_color_box(quality_status, f"FPY: {fpy:.1f}%")
    st.caption(f"Target: ≥ {t_quality}% | Scrap: {total_scrap}")

with c3:
    st.subheader("Delivery")
    st.markdown(f"# {status_indicator(delivery_status)}")
    status_color_box(delivery_status, f"Prod: {total_good}/{int(period_target)}")
    st.caption(f"Target: {int(period_target)} units")

with c4:
    st.subheader("Cost")
    st.markdown(f"# {status_indicator(cost_status)}")
    status_color_box(cost_status, f"Downtime: {total_downtime_min:.0f} min")
    st.caption(f"Target: ≤ {int(period_downtime_target)} min")

st.divider()

# --- Actions ---
st.subheader("Quick Actions")
with st.expander("Report Safety Incident"):
    with st.form("safety_form"):
        desc = st.text_area("Incident Description")
        submitted = st.form_submit_button("Log Incident")
        if submitted:
            if desc:
                log_safety_incident(selected_line_id, date.today().isoformat(), desc)
                st.success("Incident logged successfully. Refreshing...")
                st.rerun()
            else:
                st.error("Please provide a description.")

st.info("Use the Executive Summary Dashboard to manage corrective actions.")

