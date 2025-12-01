mplementing Two-Tier SQDC Lean Dashboards in Streamlit Operator Terminal

To add a two-tier Lean dashboard (SQDC boards) to the Streamlit Operator Terminal app, we should proceed in a structured way. This involves defining standard SQDC metrics, extending the database as needed, and creating two new Streamlit pages: one for Value-Stream (Line) Level SQDC and one for an Executive Summary. Below are clear next steps and recommendations:

1. Define Standard SQDC Metrics (Safety, Quality, Delivery, Cost)

First, clarify the key metrics under each SQDC category, using standard Lean definitions:

Safety: Track workplace safety incidents. Typically measured by number of accidents, near-misses, or days without incident
leandatapoint.com
. Goal: Zero incidents (green if 0, red if any incident occurs).

Quality: Measure product quality outcomes. Common metrics include scrap/defect count or First-Pass Yield (FPY) (percentage of products meeting quality on first try)
leandatapoint.com
. Goal: High FPY or low defects/scrap (set a target such as FPY ≥ 95% or ≤ X defects).

Delivery: Reflect on-time production and throughput. Use metrics like production vs. target or schedule adherence/on-time delivery
leandatapoint.com
. For example, compare units produced vs. daily plan to indicate if the team is meeting schedule. Goal: 100% of plan delivered on time.

Cost: Track operational efficiency and waste. In absence of direct cost data, use proxy metrics such as downtime (lost production time) or scrap/rework levels (which incur cost)
leandatapoint.com
. For instance, total downtime minutes in the period can represent cost impact (with a target to minimize this). Goal: Minimal waste/downtime (e.g. downtime under a threshold).

These categories align with lean practice where SQDC boards track performance in four key areas: Safety, Quality, Delivery, and Cost
leandatapoint.com
. Each category will have a target and actual value; meeting the target is typically marked green, while misses are amber/red, to enable visual management
leandatapoint.com
.

2. Extend the Data Model (SQLite DB) for SQDC Tracking

Next, update the repository’s SQLite database schema (db.py) to support new SQDC data:

Add a Safety Incidents table: Since safety data isn't tracked in the current schema, create a new table (e.g. safety_incidents) to log safety events. This table might include columns: id (PK), date (date or datetime of incident), line_id (optional, if incidents are tied to a specific line or value stream), description (text), and possibly severity or type (to distinguish accident vs. near-miss). For example:

CREATE TABLE IF NOT EXISTS safety_incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    line_id INTEGER,
    date TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY(line_id) REFERENCES lines(id)
);


This allows logging any safety incident with a date (and linking to a line/value stream if applicable). The Safety metric on the SQDC board can then be computed as the count of incidents in the chosen period (e.g. per day/week) – goal is 0. If no incident is logged for that day, Safety is green; if any incident exists, mark Safety red for that day
leandatapoint.com
.

Add an Action Items (Issues) table: To support executive actions on alerts/issues, introduce a table for tracking actions (similar to simple issue tracking). For example, an actions table with columns: id (PK), timestamp (when action created), line_id (which value stream or line it pertains to, nullable if global), category (text or code for S/Q/D/C related to the issue), description (text describing the issue or corrective action needed), assigned_to (optional, an operator/technician ID or just a name for who is responsible), status (e.g. "open", "closed"), and resolution_notes (text for any closing comments). Example schema:

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    line_id INTEGER,
    category TEXT NOT NULL,   -- e.g. 'Safety', 'Quality', etc.
    description TEXT NOT NULL,
    assigned_to INTEGER,      -- references operators(id) for now
    status TEXT NOT NULL,     -- e.g. 'open' or 'closed'
    resolution_notes TEXT,
    FOREIGN KEY(line_id) REFERENCES lines(id),
    FOREIGN KEY(assigned_to) REFERENCES operators(id)
);


This table will store executive action items. Initially, new actions will be inserted with status "open". We can reuse the existing operators table for assigned_to to pick an assignee (since the app has a list of operators/technicians; for now, treat managers/execs as part of this list or allow free-text assignment).

Database Migration: Implement creation of these tables in db.init_db(). Similar to how downtime_events got altered for new columns
GitHub
, use CREATE TABLE IF NOT EXISTS for the new tables. For example, after existing table creations, add:

cur.execute("""CREATE TABLE IF NOT EXISTS safety_incidents (...);""")
cur.execute("""CREATE TABLE IF NOT EXISTS actions (...);""")


This ensures the tables are created on first run. If the app might already have an existing DB, no conflict occurs due to IF NOT EXISTS. (If needed, also handle any future alterations with PRAGMA table_info checks as done for downtime_events migration
GitHub
.)

Data Seeding (if applicable): You may optionally seed initial data for demonstration, though for Safety and Actions it might be best to start empty (since ideally zero incidents and no issues to start “green”). The seed_db() can remain mostly unchanged; perhaps just ensure it doesn’t overwrite or duplicate if run again (it already skips if data exists
GitHub
). We likely won’t seed any safety incidents or actions by default (let those be created through the UI when needed). However, you could seed one example incident or action for testing the UI, then remove it later. For now, starting with none (all green) is fine.

Helper Functions: Add convenience functions in db.py to interact with these new tables:

log_safety_incident(line_id, description): inserts a new row with current timestamp or date.

get_safety_incidents(line_id, start_date, end_date): retrieves incidents in a date range (to count them for a given day/week on the board).

create_action(line_id, category, description, assigned_to): inserts a new action (with status "open").

get_actions(status=None): fetches actions (filter by status or by line/category if needed, for listing open issues on the exec dashboard).

close_action(action_id, resolution_notes): updates an action’s status to "closed" with resolution notes (similar to how maintenance view calls resolve_downtime_event with notes
GitHub
).

These functions will encapsulate the SQL for these operations. Using sqlite3 with parameter substitution or Pandas read_sql for queries is fine (consistent with how other getters work, e.g. pd.read_sql in get_lines()
GitHub
).

Note: We might not need a new table for daily targets – instead, targets can be constants or configuration. For example, daily goals for each metric can be hardcoded or configurable in code (e.g., "zero incidents", "FPY 95%", "100 units per day", "downtime < X min"). If more flexibility is needed, a simple targets table could map each line & metric to a daily goal, but initially this may be overkill. We can proceed with fixed standard targets and adjust if needed.

3. Build the Value-Stream Level SQDC Board Page (Tier 1 Dashboard)

Create a new Streamlit page (e.g. pages/5_Value_Stream_SQDC.py) for the value stream level SQDC board. This page focuses on “winning the day/week” for a single value stream (likely corresponding to a production line or department). Key elements to implement:

Page Setup & Filters: Use st.set_page_config(page_title="SQDC Board", layout="wide"). Include controls to select the context:

Value Stream/Line selector: If the app has multiple lines (e.g. Line A, Line B from seed data
GitHub
), provide a dropdown to select which line’s SQDC board to view. You can reuse get_lines() to populate options.

Date (and Range) selection: Allow choosing the date or range for the dashboard. By default, show today’s metrics (the current shift/day). A st.date_input (default today) can be used. If “week” view is desired, you could offer a toggle or radio button for Day vs. Week. For example, a radio: view_scope = st.radio("View", ["Today", "This Week"]). If “This Week” is selected, you can consider the week-to-date (e.g. starting Monday to current date) or the last 7 days. In either case, fetch data accordingly (and perhaps show an aggregated status or trend over that period).

Shift filter (optional): If needed, you could reuse the SHIFTS defined in config.py to filter by shift times
GitHub
. However, since SQDC boards are typically daily, it might suffice to use “All Day” by default (covering the full day). If you want parity with the existing Supervisor Dashboard filter, you can include a shift dropdown defaulting to "All Day" and filter events by the selected shift’s time window.

Calculate Metrics for Selected Line & Period: Query the database for that line and time window:

Safety: Count safety incidents for that line in the period. get_safety_incidents(line_id, date_start, date_end) can return a dataframe or count; if count > 0, mark Safety = RED (with the count). If 0, mark GREEN (e.g. “0 incidents”). You might also display a secondary metric like “X days since last incident” to add context (this could be computed by looking at the most recent incident date for that line).

Quality: Compute quality performance. A straightforward metric is scrap count (sum of quality_events.quantity) for the period and/or First Pass Yield. FPY = good output / (good + scrap). You can get good output by summing production_counts.good_quantity for that line & period, and scrap by summing quality_events.quantity. Then FPY (%) = good/(good+scrap)*100
GitHub
. Display either FPY (e.g. “FPY 92% vs 95% target”) or scrap count (e.g. “Scrap = 10 units, target <5”). Use red/green coloring based on meeting the target.

Delivery: Determine if the line is meeting production schedule. If a daily production target exists, compare it to actual good production count for the day. For example, if Line A’s plan is 100 units/day and actual good count is 80, mark Delivery as red (80/100 achieved). In absence of an explicit target in the DB, you might derive one from work orders (e.g. if a work order’s target_quantity is for a week, divide by days) or set a notional daily goal for demonstration. Another approach is to use uptime as a proxy: since downtime events are tracked, you could compute Uptime % for the line (minutes running vs. total minutes in shift)
GitHub
GitHub
. However, uptime overlaps with efficiency/cost. It may be simplest to stick to production output vs plan as the Delivery metric. Display something like “Production: 80/100 units (80% of plan)”. Green if ≥100%, else red.

Cost: Use efficiency/waste metrics. A convenient choice is Total Downtime Minutes (unplanned losses of capacity). Sum downtime_events.duration_minutes for that line in the period (for active events that cross the period, include the portion within the window). Alternatively or additionally, use the scrap quantity again but converted to a cost (e.g. if each scrap has an estimated cost, total scrap cost). For now, summing downtime gives a sense of lost productivity cost. For example, “Downtime: 30 minutes” and set a target (say < 20 min per shift). Mark green if below target, red if above.

People/Morale (optional): Some Lean boards include a “People” or morale category (making it SQDCP). Since we stick to SQDC as requested, we won’t add a separate category, but any ergonomic or staffing issues could be folded under Safety or left out for now.

Use Pandas or SQL queries to gather these metrics. For example, for downtime minutes:

df_dt = pd.read_sql(f"""
    SELECT SUM(duration_minutes) as total_dt
    FROM downtime_events
    WHERE line_id=? AND start_time >= ? AND end_time <= ?;
""", conn, params=[line_id, start_ts, end_ts])
total_dt = df_dt["total_dt"][0] or 0


(Adjust logic if an event’s end_time is null or overlaps the window.) Similar aggregation can be done for quality_events and production_counts. If using Pandas, you can also read all events for that line then filter by timestamp in code.

UI Layout – Visual Board: Present the four metrics clearly, emulating a physical SQDC board:

Use four columns (st.columns(4)) to layout Safety, Quality, Delivery, Cost side by side. In each column, use a consistent format:

A heading or metric name (e.g. st.subheader("Safety") or an icon/emoji for each).

The metric value and status. Streamlit’s st.metric(label, value, delta) could be useful, but it’s primarily for numeric deltas. Instead, consider using colored text or an emoji to indicate status. For example:

If Safety is good: st.write("✅ **0 Incidents**") (green check mark) or use st.success("0 Incidents") which gives a green box. If not good: st.write("❌ **1 Incident**") or st.error("1 Incident (attention!)").

Similarly for other categories: e.g., Quality: st.success(f"FPY {fpy:.1f}%") if above target, or st.error(f"FPY {fpy:.1f}%") if below. You could also show the target in smaller text (e.g. “FPY 90% (Target 95%)”).

Another approach is to use HTML/CSS for colored blocks (as done in Maintenance view for statuses
GitHub
), but simple use of st.success/st.error or emoji can suffice and keeps the UI simple.

Trend/Detail (optional): If viewing a week, you might show a trend of each day’s performance. For example, a small table or chart of each day’s metric (with green/red coloring) can be included. This can help illustrate “winning the week” by showing which days met targets. A simple implementation: if view_scope == "This Week", compute the metrics for each day Monday–today and perhaps display a small dataframe or chart. For instance, a DataFrame like:

Date      SafetyIncidents  FPY(%)   Prod_vs_Plan(%)   Downtime_min
2025-12-01      0           98%         105%             10
2025-12-02      1           94%          90%             30
... 


You could then use st.table or an Altair chart (though coloring individual cells green/red in a table might need unsafe_allow_html or DataFrame styling). This is an enhancement for visualization; if time is short, it can be added later since the primary goal is the current status board.

Interaction - Logging Issues: On the value-stream page, allow operators or supervisors to update metrics if needed:

Provide a way to log a safety incident if one occurs. For example, a small form (st.form) with a text input for description, which on submit calls log_safety_incident(line_id, desc) and adds the incident (date = today by default). This would turn the Safety metric red and record the incident for traceability. This is in line with operators “reporting incidents” on the board
leandatapoint.com
.

You might also allow logging other events if not already covered (but downtime and quality are already handled in Operator Panel). The SQDC board is more for viewing status, but having a quick incident report button is useful for completeness.

If an incident is logged or any metric is off-track, you could display a prompt or link like “⚠️ Not meeting target – see if an action is needed” to hint that the exec level might create an action (the actual action creation will be on the exec page).

4. Build the Executive Summary Dashboard Page (Tier 2 Dashboard)

Create another Streamlit page (e.g. pages/6_Executive_Summary.py) for the summary dashboard that aggregates multiple SQDC boards. This is the higher-tier view for managers/executives, providing a plant-wide or multi-value-stream overview
leandatapoint.com
. Key features:

Overall Status Matrix: Display an at-a-glance matrix of all value streams vs. SQDC metrics. A clear way to do this is a table where each row is a Line/Value Stream and columns are Safety, Quality, Delivery, Cost status:

For each line, gather the metrics as in the line-level board (likely for the current day by default, or allow the exec to select date/week similarly). You can reuse the calculations or even call the same functions used for the individual page. For simplicity, assume we show today’s performance of each line side-by-side.

Visualization approach 1 – Status Grid: Use colored indicators in each cell to denote if target met. For example, a cell could display "🟢" or "✅" if that metric is green, or "🔴" or "❌" if not. Alongside the icon, show a brief value or percentage. E.g., under Quality for Line A: “❌ 90% FPY” if below target, or “✅ 98% FPY” if good. This way an executive can scan the grid and immediately spot any red markers.

Implementation: Streamlit doesn’t support cell-level styling in st.table easily, so you can construct this manually. One method is to loop through lines and use st.columns for each row. For each line:

cols = st.columns(5)  # 1 for line name, 4 for SQDC
cols[0].write(f"**{line_name}**")
# then for each metric category, put colored text
cols[1].write("✅ 0" if incidents==0 else "🔴 1")  # Safety example
cols[2].write("✅ 95% FPY" if fpy >= 95 else f"🔴 {fpy:.0f}% FPY")
... and so on


This will render a pseudo-table row by row. (Alternatively, construct an HTML table with colored background in Markdown, but that can be messy. The column approach is straightforward for a few lines.)

You can also include a summary row like "All Lines Combined" if that makes sense (for some metrics summing is meaningful: e.g. total incidents, average FPY, total output vs total plan, total downtime). This is optional.

Visualization approach 2 – Charts: In addition to the grid, provide some charts comparing performance across value streams, since the user is open to multiple (even redundant) views:

A bar chart per category: e.g. one bar chart for Quality showing FPY or defect count for each line; another for Delivery showing % of plan achieved per line; etc. This gives a quick comparison of which line is lagging. You can use st.bar_chart or Altair. For instance, use a DataFrame with index = line names and columns = metrics, then st.bar_chart(df[['FPY']]) to plot quality by line. Or explicitly use Altair to color bars red/green based on meeting target.

A heatmap view: For example, an Altair chart with line on the Y axis, category on X axis, and color indicating performance value or a binary meet/miss. Since we essentially have binary (met = green, not met = red), a heatmap could just reflect that (two colors). However, Altair will require numeric data for color scale; you could map met->1, miss->0. But this might not add much beyond the grid already shown, unless you use a continuum for how close to target (e.g. FPY% or downtime minutes scaled). If interested, one could set up a small dataframe:

data = []
for each line:
    data.append({"Line": line_name, "Metric": "Safety", "Status": 1 if incidents==0 else 0})
    ... for each category
chart = alt.Chart(pd.DataFrame(data)).mark_rect().encode(
    x='Metric:O', y='Line:O',
    color=alt.Color('Status:Q', scale=alt.Scale(domain=[0,1], range=['red','green']))
)
st.altair_chart(chart)


This would color a 4xN grid of cells. Given that we have the textual matrix, this is a nice-to-have visualization. The user did mention heatmap as an option, so including it as an alternative visualization is a good idea.

Trend charts: If execs want to see trends, you could allow a date range selection and then plot trends for each line. For example, a line chart of daily Delivery % for each line over the past week, or a stacked bar of total scrap by line, etc. Since the prompt specifically said aggregated data from multiple boards, focus on cross-line comparison at the current time frame. Trend over time might be more complex to present on one chart with multiple lines; it can be considered in future iterations.

Include a brief explanatory legend if needed (e.g. “Green ✅ = at or better than goal; Red ❌ = below goal”).

Executive Actions & Alerts: A critical interactive element for the exec dashboard is the ability to respond to problems:

Alert Detection: In the code, identify any metric that is off-target (e.g. any red cell). You could compile a list of “alerts” such as Line B – Delivery below target, Line A – Safety incident occurred. Display these prominently (e.g. with st.warning or an emoji) to draw attention. For example:

issues = []
if incidents_A > 0: issues.append("Line A Safety incident")
if fpy_A < target: issues.append("Line A Quality below target")
...
for issue in issues:
    st.write(f"⚠️ **{issue}**")
else:
    if not issues: st.write("✅ All value streams meeting targets.")


This textually lists the alerts.

Action Creation Form: Provide a form for executives to create a new action item in response to an alert:

The form can include:

Line (Value Stream) dropdown: choose the affected line (or “All”/None if the action is broader).

Category dropdown: one of Safety/Quality/Delivery/Cost (this might be pre-selected if you initiate the form from a specific alert, but a simple form can let them choose).

Description text area: to describe the issue and the corrective action needed. Encourage a concise but descriptive entry (e.g. “Investigate root cause of repeated machine jams causing downtime on Line B”).

Assignee dropdown: list of operators/technicians/managers to assign. We can reuse get_operators()
GitHub
 for a list of names (this might include people who are not actually execs, but at least one can choose a supervisor or technician responsible). If the list is not ideal, an alternative is a free-text for “Assigned to (name)”.

Submit button: on submit, call create_action() to insert the new action into the DB (with status "open"). You should capture the current timestamp (use datetime.now().isoformat() for timestamp). After creation, you can st.success("Action created!") and perhaps immediately display it in the Open Actions list.

If possible, tie this to alerts for user convenience. For example, next to each listed alert, you could put a small button “Create Action”. If that button is clicked, it could auto-fill the form with that line & category. In Streamlit, you might handle this by setting session state or using query params. Simpler might be to have the form always visible and just let the user select the relevant info manually.

Displaying Action Items: Show a table or list of Open Actions so executives can track issues to closure:

Query the actions table for all open actions (status='open'). Display them, perhaps with columns: Date/Time, Line, Category, Description, Assigned To, and maybe a button or link to mark as resolved. You can use st.dataframe for a quick table view (hide the ID, show other fields). For a nicer look, you might format it as:

open_actions = get_actions(status="open")
if not open_actions.empty:
    for _, act in open_actions.iterrows():
        st.markdown(f"**[{act['line_name'] or 'All'} - {act['category']}]** {act['description']}  — *Assigned:* {act['assignee_name'] or 'Unassigned'}")
        if st.button(f"Close #{act['id']}", key=f"close_{act['id']}"):
            # if clicked, show a text_input for resolution then confirm close


Alternatively, list them and use an expander to add a resolution/comment and close, similar to how Maintenance View handles resolving downtime
GitHub
. For example, inside each action listing, if the exec (or whoever) wants to close it:

Provide a text input for resolution notes.

A “Close” button that calls close_action(id, notes) to set status="closed" and save notes.

After closing, refresh the list (e.g. with st.experimental_rerun()).

Commenting: If you need more than one comment per action (like a discussion thread), you could add an action_comments table or allow editing the description. Given the scope, a single resolution note might suffice (the assumption is these action items are like tasks that get one resolution when completed). In the future, if richer discussion is needed, integrating with an external tool or a more complex UI might be better. For now, basic commenting can be done via the resolution field when closing, or by updating the description if still open.

Alerts/Notifications: The prompt mentions sending alerts. In a real app, you might integrate email or messaging when an action is created or when a metric goes red. For now, we can simulate an alert by simply highlighting it in the UI (as described above). We can note in comments that an enhancement could be to trigger an email or Slack message when an action is created or when a safety incident is logged, etc. This could be achieved by calling an email API or similar within the Streamlit app, but that’s beyond the MVP. It’s enough to plan it as a future improvement.

By implementing the above, executives can see organization-wide performance at a glance and directly initiate corrective actions for any problem areas, fulfilling the tiered SQDC approach (operators address issues in real-time on their board, and higher management reviews aggregated metrics and ensures accountability through actions)
leandatapoint.com
.

5. Integration and Testing

Finally, integrate these changes and test the whole flow:

Add the new pages to the app: Save the new files in the pages/ directory with the numeric prefix to appear in the sidebar (they will auto-register in Streamlit’s multipage setup). For example, 5_Value_Stream_SQDC.py will appear after the existing pages (Operator, Supervisor, Admin, Maintenance) in the sidebar. You may want to rename the page titles via st.title() or st.header() at top of each page to something like "Value Stream SQDC Board" and "Executive Summary Dashboard" for clarity.

Update navigation info: If the main app.py or README references the pages, update them. The current app.py welcome text lists Operator, Supervisor, Admin views
GitHub
. We should add mentions of the new dashboards, e.g.: “- SQDC Board: Daily Safety/Quality/Delivery/Cost metrics for each value stream (line). - Executive Summary: Aggregated SQDC metrics and issue tracking for management.” This ensures users know about the new pages.

Test metrics calculations: Run the app and simulate data to verify calculations:

Log a downtime event and a production count and ensure Delivery% or downtime minutes reflect correctly on the SQDC pages.

Log a quality event (scrap) and see that Quality metric (FPY or defects) updates accordingly.

Try logging a safety incident via the new form and confirm Safety turns red and the incident appears in the exec summary.

Create an action from the exec page and then check the database (or UI list) to ensure it’s recorded. Test closing an action with a resolution note and ensure it’s removed from open list (and ideally appears under a “Closed” list if you choose to show that or just not shown).

UI refinements: Adjust formatting for readability. Keep paragraphs and sections concise on the Streamlit page (avoid walls of text – use headers, subheaders for each category maybe). Since the user is fine with multiple visualizations, see that none are too redundant/confusing. You might include both the status grid and a bar chart, but if it feels cluttered, use st.expander to hide one by default or allow toggling the view (e.g., a selectbox “View Mode: [ Status Grid | Charts ]”). Given "fine to be redundant," it's okay to show both initially and gather feedback.

Ensure performance is okay: With SQLite and Pandas on what is likely small data (one day of events), this should be fine. If you loop through lines and run queries repeatedly, that’s okay for a handful of lines. If there were many lines, you’d optimize by pulling all needed data in one go. For now, clarity is more important than premature optimization.

By following these steps, the repository will be extended to support a two-tier Lean daily management system:

The Value Stream SQDC page acts as a Tier-1 board where supervisors and teams see their daily S/Q/D/C metrics (and can take immediate action on the floor to “win the day”).

The Executive Summary page serves as a Tier-2 board, rolling up those metrics so leadership can identify systemic issues and assign actions for continuous improvement
leandatapoint.com
. This hierarchy aligns with lean best practices (as seen in Danaher and other Lean organizations) where Safety and Quality come first, followed by Delivery and Cost
leanblog.org
.

With the standard SQDC metrics in place and interactive features to log incidents and manage action items, the app will support daily huddle meetings and escalation of issues in a digital, streamlined way.