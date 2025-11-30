import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta, time
from config import SHIFTS
from db import (
    get_downtime_summary, get_quality_summary, get_production_summary,
    get_lines
)

st.set_page_config(page_title="Supervisor Dashboard", layout="wide")
st.title("Supervisor Dashboard")

# --- 1. Filters ---
st.sidebar.header("Filters")

# Date Selection
selected_date = st.sidebar.date_input("Select Date", datetime.now())

# Shift Selection
selected_shift_name = st.sidebar.selectbox("Select Shift", options=list(SHIFTS.keys()))
shift_times = SHIFTS[selected_shift_name]

# Calculate Start and End Timestamps
start_time_str = f"{selected_date}T{shift_times['start']}:00"
# Handle overnight shift logic (simple MVP: if end < start, add 1 day to end date)
# For MVP, let's keep it simple and assume same day unless specified.
# Ideally, we check if end_time < start_time
start_t = datetime.strptime(shift_times['start'], "%H:%M").time()
end_t = datetime.strptime(shift_times['end'], "%H:%M").time()

start_dt = datetime.combine(selected_date, start_t)
if end_t < start_t:
    end_dt = datetime.combine(selected_date + timedelta(days=1), end_t)
else:
    end_dt = datetime.combine(selected_date, end_t)

start_iso = start_dt.isoformat()
end_iso = end_dt.isoformat()

# Filter by Line (Optional)
lines_df = get_lines()
line_options = {row["name"]: row["id"] for _, row in lines_df.iterrows()}
selected_line_name = st.sidebar.selectbox("Filter by Line (Optional)", ["All"] + list(line_options.keys()))
selected_line_id = line_options[selected_line_name] if selected_line_name != "All" else None

st.write(f"**Viewing Data For:** {selected_date} | {selected_shift_name} ({start_iso} to {end_iso})")

# --- 2. Data Retrieval ---
downtime_df = get_downtime_summary(start_iso, end_iso)
quality_df = get_quality_summary(start_iso, end_iso)
production_df = get_production_summary(start_iso, end_iso)

# Filter by Line if selected
if selected_line_id:
    if not downtime_df.empty:
        downtime_df = downtime_df[downtime_df['line_id'] == selected_line_id]
    if not quality_df.empty:
        quality_df = quality_df[quality_df['line_id'] == selected_line_id]
    if not production_df.empty:
        production_df = production_df[production_df['line_id'] == selected_line_id]

# --- 3. Line / Machine Summary ---
st.subheader("Production Summary")

# Aggregate Data per Machine
# We need a list of all relevant machines.
# If a machine had no events, it might not be in the DFs. 
# Ideally we query all machines first. But for MVP, we can aggregate what we have.

machine_stats = {}

# Process Downtime
if not downtime_df.empty:
    for _, row in downtime_df.iterrows():
        m_name = row['machine_name']
        if m_name not in machine_stats:
            machine_stats[m_name] = {'downtime_min': 0, 'events': 0, 'scrap': 0, 'good': 0}
        
        # Calculate duration inside window
        # MVP: Use pre-calculated duration or calculate now if active
        if pd.isna(row['end_time']):
             # Active event: duration = now - start (capped at window end)
             # But for historical window, it's min(now, window_end) - max(start, window_start)
             # Let's simplify: if active, calculate up to NOW (or window end)
             event_end = min(datetime.now(), end_dt)
             event_start = datetime.fromisoformat(row['start_time'])
             # Ensure start is not before window start for calculation (metrics within window)
             calc_start = max(event_start, start_dt)
             duration = (event_end - calc_start).total_seconds() / 60.0
             duration = max(0, duration)
             machine_stats[m_name]['downtime_min'] += duration
        else:
             # Closed event
             # MVP: Use stored duration_minutes. 
             # Refinement: Only count intersection with window.
             # Let's stick to MVP: sum stored duration if it started in window (or intersects).
             # The query returns intersecting events.
             machine_stats[m_name]['downtime_min'] += (row['duration_minutes'] if row['duration_minutes'] else 0)

        machine_stats[m_name]['events'] += 1

# Process Quality
if not quality_df.empty:
    for _, row in quality_df.iterrows():
        m_name = row['machine_name']
        if m_name not in machine_stats:
            machine_stats[m_name] = {'downtime_min': 0, 'events': 0, 'scrap': 0, 'good': 0}
        machine_stats[m_name]['scrap'] += row['quantity']

# Process Production
if not production_df.empty:
    for _, row in production_df.iterrows():
        m_name = row['machine_name']
        if m_name not in machine_stats:
            machine_stats[m_name] = {'downtime_min': 0, 'events': 0, 'scrap': 0, 'good': 0}
        machine_stats[m_name]['good'] += row['good_quantity']

# Convert to DataFrame
summary_data = []
total_window_min = (end_dt - start_dt).total_seconds() / 60.0

for m_name, stats in machine_stats.items():
    uptime_min = total_window_min - stats['downtime_min']
    uptime_pct = (uptime_min / total_window_min) * 100 if total_window_min > 0 else 0
    
    summary_data.append({
        "Machine": m_name,
        "Downtime (min)": round(stats['downtime_min'], 1),
        "DT Events": stats['events'],
        "Good Qty": stats['good'],
        "Scrap Qty": stats['scrap'],
        "Uptime %": round(uptime_pct, 1)
    })

if summary_data:
    st.dataframe(pd.DataFrame(summary_data), hide_index=True)
else:
    st.info("No data found for the selected period.")

# --- 4. Charts ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Downtime Pareto (Minutes)")
    if not downtime_df.empty:
        # Group by reason
        # We need to recalculate duration for active events for the chart too, 
        # but for MVP let's just use sum of duration_minutes (and estimate active).
        # To be consistent with table, we should use the same logic, but it's harder in pure pandas without iteration.
        # Let's just group by reason description.
        
        # Fill NaN duration for active events with calculation
        def calc_dur(row):
            if pd.notnull(row['duration_minutes']):
                return row['duration_minutes']
            # Estimate
            start = datetime.fromisoformat(row['start_time'])
            end = min(datetime.now(), end_dt)
            return max(0, (end - start).total_seconds() / 60.0)

        downtime_df['calc_duration'] = downtime_df.apply(calc_dur, axis=1)
        
        pareto_dt = downtime_df.groupby("reason_description")['calc_duration'].sum().reset_index()
        pareto_dt = pareto_dt.sort_values("calc_duration", ascending=False)
        
        c = alt.Chart(pareto_dt).mark_bar().encode(
            x=alt.X('reason_description', sort='-y', title="Reason"),
            y=alt.Y('calc_duration', title="Minutes"),
            tooltip=['reason_description', 'calc_duration']
        )
        st.altair_chart(c, theme="streamlit")
    else:
        st.write("No downtime data.")

with col2:
    st.subheader("Scrap Pareto (Quantity)")
    if not quality_df.empty:
        pareto_q = quality_df.groupby("reason_description")['quantity'].sum().reset_index()
        pareto_q = pareto_q.sort_values("quantity", ascending=False)
        
        c = alt.Chart(pareto_q).mark_bar().encode(
            x=alt.X('reason_description', sort='-y', title="Reason"),
            y=alt.Y('quantity', title="Quantity"),
            tooltip=['reason_description', 'quantity']
        )
        st.altair_chart(c, theme="streamlit")
    else:
        st.write("No scrap data.")

