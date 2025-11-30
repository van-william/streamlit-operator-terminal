Here’s a concrete spec you can hand straight to Codex / Cursor to build a **simple Streamlit digital Andon + downtime tracking app**.

I’ll structure it as:

1. Product vision & scope
2. Personas & key workflows
3. Data model
4. App pages & UI behavior
5. Core metrics & logic
6. Technical design notes for Streamlit
7. Starter file structure & skeleton code

---

## 1. Product Vision & Scope

**Goal:**
Simple, tablet-friendly Streamlit app that lets operators and supervisors:

* Log **downtime events** with reasons, timestamps, and affected work orders.
* Track **downtime timers** (start / stop).
* Log **quality issues / scrap** by cause.
* Associate all events with **operator**, **work order**, **machine/line**.
* Provide a simple **dashboard** showing uptime, downtime, and basic performance metrics for the current shift.

**MVP Scope:**

* Single site, multiple lines/machines.
* No user auth initially (just select operator from dropdown).
* Local storage in **SQLite** (or CSV as step 0, but SQLite preferred).
* Runs on factory network via `streamlit run app.py`, used on tablets or desktop.

---

## 2. Personas & Key Workflows

### Personas

1. **Operator**

   * Needs to quickly log downtime & quality events.
   * Should not have to type much; mostly tap/select.

2. **Supervisor / Team Lead**

   * Wants to see current line status (running vs down).
   * Wants summary of downtime by reason, quality issues, and output vs target.

3. **Process Engineer (later)**

   * Wants history and Pareto of downtime and quality over days/weeks.

For MVP, focus on **Operator and Supervisor**.

### Key Operator Workflows

* Start shift: choose **line**, **machine**, **work order**, **operator name**.
* When machine stops, tap **“Start Downtime”** → timer starts.
* Choose **downtime cause** (from predefined list).
* When running resumes, tap **“End Downtime”** → record duration.
* Log **scrap / defects**: enter quantity and cause.
* Optionally log **good quantity produced** vs target.

### Key Supervisor Workflows

* See **live status** of each line:

  * RUNNING / DOWN
  * Current downtime reason & elapsed time (if down)
* See **current shift summary**:

  * Total downtime (min), by cause
  * Scrap quantity, by cause
  * Simple uptime % and production count vs target

---

## 3. Data Model

Use a small **SQLite DB**. Tables (MVP):

### 3.1. `lines`

* `id` (PK)
* `name` (text)
* `description` (text, nullable)

### 3.2. `machines`

* `id` (PK)
* `name` (text)
* `line_id` (FK → lines.id)
* `description` (text, nullable)

### 3.3. `operators`

* `id` (PK)
* `name` (text) – simple free text; no auth for now
* `badge_id` (text, optional)

### 3.4. `work_orders`

* `id` (PK)
* `wo_number` (text)
* `part_number` (text)
* `target_quantity` (int, nullable)
* `due_date` (text or date, nullable)
* `line_id` (FK, nullable)

*(For MVP, these can be entered manually or seeded; later load from ERP.)*

### 3.5. `downtime_reasons`

* `id` (PK)
* `code` (text, e.g. “MECH”, “MATL”, “CHANGEOVER”)
* `description` (text)
* `category` (text, e.g. “Planned”, “Unplanned”)

### 3.6. `quality_reasons`

* `id` (PK)
* `code` (text)
* `description` (text)
* `category` (text, e.g. “Defect”, “Rework”)

### 3.7. `downtime_events`

* `id` (PK)
* `machine_id` (FK)
* `line_id` (FK)
* `work_order_id` (FK, nullable)
* `operator_id` (FK, nullable)
* `reason_id` (FK → downtime_reasons.id)
* `start_time` (datetime)
* `end_time` (datetime, nullable while active)
* `duration_minutes` (real, computed when closed)
* `notes` (text, nullable)

### 3.8. `quality_events`

* `id` (PK)
* `machine_id` (FK)
* `line_id` (FK)
* `work_order_id` (FK, nullable)
* `operator_id` (FK, nullable)
* `reason_id` (FK → quality_reasons.id)
* `quantity` (int)
* `timestamp` (datetime)
* `notes` (text, nullable)

### 3.9. `production_counts`

* `id` (PK)
* `machine_id` (FK)
* `line_id` (FK)
* `work_order_id` (FK)
* `operator_id` (FK, nullable)
* `good_quantity` (int)
* `scrap_quantity` (int, default 0)
* `timestamp` (datetime)

*(Optionally, instead of counts, you can log cumulative counter snapshots.)*

---

## 4. App Pages & UI Behavior

Use **Streamlit multipage** pattern or a sidebar menu.

### Page 1: “Operator Panel”

**Purpose:** One-stop screen for operators on the line.

**Sections:**

1. **Context Selection**

   * Dropdowns:

     * Line
     * Machine (filtered by Line)
     * Work Order
     * Operator
   * This context is stored in `st.session_state`.

2. **Current Status / Downtime Timer**

   * If no active downtime event:

     * Show status: **RUNNING** (green).
     * Button: **“Start Downtime”**.

       * On click:

         * Require a **Downtime Reason** selection (selectbox).

           * If reason not chosen yet, ask in modal-style block or another select.
         * Create `downtime_events` row with `start_time=now`, `end_time=NULL`.
         * Store `active_downtime_id` in `st.session_state`.
   * If an active downtime event exists:

     * Show status: **DOWN** (red).
     * Show selected reason and **elapsed time** (live updating).
     * Button: **“End Downtime”**.

       * On click:

         * Set `end_time=now`.
         * Compute `duration_minutes`.
         * Persist to DB.
         * Clear `active_downtime_id` from `session_state`.

3. **Quality / Scrap Logging**

   * Simple form:

     * Quantity (number input)
     * Quality Reason (selectbox)
     * Optional text field for notes.
     * Submit button: inserts into `quality_events`.
   * Optionally a second form:

     * “Log Good Production”: good quantity entry + timestamp → adds to `production_counts`.

4. **Recent Events**

   * Table showing **last 10 downtime events** and **last 10 quality events** for the chosen line/machine/WO.
   * Columns: start_time, end_time, duration, reason, operator for downtime; time, qty, reason for quality.

**UX Notes:**

* Layout optimized for touch:

  * Big buttons (`st.button`) for start/stop.
  * Minimal typing; mostly dropdowns and number inputs.
* Persist context in `st.session_state` so page reruns don’t lose current selections.

---

### Page 2: “Supervisor Dashboard”

**Purpose:** Overview of current shift performance by line/machine.

**Inputs:**

* Date and shift filter:

  * Date picker (default **today**).
  * Shift drop-down (e.g., “All Day”, “Shift 1”, “Shift 2”).
  * Implement shift as time windows (e.g., 06:00–14:00).

**Widgets & Views:**

1. **Line / Machine Summary Table**

   * For each machine (or line):

     * Status: RUNNING or DOWN (if active downtime event).
     * Total downtime (min) in the selected time window.
     * Number of downtime events.
     * Total scrap quantity.
     * Good quantity.
     * Uptime % (simple calculation, see section 5).

2. **Downtime Pareto Chart**

   * Bar chart: total downtime minutes by downtime reason, descending.
   * Use `st.bar_chart` or `altair`.

3. **Quality Pareto Chart**

   * Bar chart: scrap quantity by quality reason.

4. **Trend Over Time (Optional MVP+1)**

   * Line chart: downtime minutes per hour or scrap per hour.

---

### Page 3: “Admin / Master Data”

**Purpose:** Configure lines, machines, operators, and reason codes.

**MVP Version:**

* Use simple editable tables via `st.data_editor` or forms.
* Subsections:

  * Lines & Machines
  * Operators
  * Downtime Reasons
  * Quality Reasons

**Behavior:**

* Allow adding new records via form at top.
* Show existing data in table form.
* For MVP, allow delete/edit only via editing table rows or not at all (just add-only is acceptable early on).

---

## 5. Core Metrics & Logic

Keep this simple but structured so it’s easy to extend to OEE later.

### 5.1. Time Window

* For dashboard metrics, define a **time window**:

  * e.g., from `shift_start` to `shift_end` (depends on selected date and shift).
* Total time window (minutes) = `(shift_end - shift_start)`.

### 5.2. Downtime Calculations

For each machine within time window:

* **Total downtime minutes**:

  * Sum of `duration_minutes` for all `downtime_events` whose time intersects the window.
  * Edge case: events partially overlapping window → adjust duration accordingly (MVP can ignore and assume all inside).

* **Uptime minutes**:

  * `uptime_minutes = total_window_minutes - total_downtime_minutes`.

* **Uptime %**:

  * `uptime_percent = uptime_minutes / total_window_minutes * 100`.

### 5.3. Quality / Scrap Metrics

Within the time window:

* **Total scrap quantity**:

  * Sum of `quality_events.quantity`.

* **Scrap by reason**:

  * Group `quality_events` by `quality_reasons.description` and sum.

* **Good quantity**:

  * Sum of `production_counts.good_quantity`.

* **First pass yield (simple)**:

  * `FPY = good_quantity / (good_quantity + scrap_quantity)` if denominator > 0.

*(All formulas can be implemented in Pandas.)*

---

## 6. Technical Design Notes for Streamlit

### 6.1. Tech Stack

* **Frontend & app framework:** Streamlit.
* **Backend storage:** SQLite (using `sqlite3` or SQLAlchemy).
* **Data manipulation:** Pandas.

### 6.2. Structure & Patterns

* Use a **DB helper module** that exposes functions like:

  * `init_db()`
  * `get_lines()`, `get_machines(line_id)`, etc.
  * `create_downtime_event(...)`
  * `close_downtime_event(event_id)`
  * `get_active_downtime(machine_id)`
  * `get_shift_downtime(line_id, start, end)` etc.

* Use `st.session_state` for:

  * Current line, machine, operator, WO.
  * Active downtime event ID per machine.

* Use a simple **“shift config”** dictionary for standard shift times:

  ```python
  SHIFTS = {
      "All Day": {"start": "00:00", "end": "23:59"},
      "Shift 1": {"start": "06:00", "end": "14:00"},
      "Shift 2": {"start": "14:00", "end": "22:00"},
      "Shift 3": {"start": "22:00", "end": "06:00"},  # next day edge case
  }
  ```

### 6.3. Performance & Concurrency

* MVP can ignore heavy concurrency issues.
* App will be used by a small number of tablets; SQLite should be fine.
* Later: can move DB to Postgres / cloud.

---

## 7. Starter File Structure & Skeleton Code

A simple structure Codex can generate:

```text
andon_app/
  app.py                # main entry, menu/router
  pages/
    1_Operator_Panel.py
    2_Supervisor_Dashboard.py
    3_Admin_Config.py
  db.py                 # DB init + query helpers
  config.py             # constants, shifts, etc.
  requirements.txt
```

### `app.py` (router + basic setup) – example skeleton

```python
import streamlit as st
from db import init_db

st.set_page_config(
    page_title="Digital Andon",
    layout="wide",
)

def main():
    st.title("Digital Andon / Downtime Tracker")
    st.write("Use the sidebar to navigate between Operator, Supervisor, and Admin views.")

    st.info("This is a simple MVP andon system built with Streamlit.")

if __name__ == "__main__":
    init_db()
    main()
```

### `db.py` (minimal idea; Codex fills out):

```python
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("andon.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Example: create tables if not exists
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            line_id INTEGER,
            description TEXT,
            FOREIGN KEY (line_id) REFERENCES lines(id)
        );

        CREATE TABLE IF NOT EXISTS operators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            badge_id TEXT
        );

        CREATE TABLE IF NOT EXISTS downtime_reasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT
        );

        CREATE TABLE IF NOT EXISTS downtime_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER,
            line_id INTEGER,
            work_order_id INTEGER,
            operator_id INTEGER,
            reason_id INTEGER,
            start_time TEXT,
            end_time TEXT,
            duration_minutes REAL,
            notes TEXT
        );
        """
    )

    conn.commit()
    conn.close()

def create_downtime_event(machine_id, line_id, work_order_id, operator_id, reason_id, notes=""):
    conn = get_connection()
    cur = conn.cursor()
    start_time = datetime.utcnow().isoformat()
    cur.execute(
        """
        INSERT INTO downtime_events (machine_id, line_id, work_order_id, operator_id, reason_id, start_time, end_time, duration_minutes, notes)
        VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?)
        """,
        (machine_id, line_id, work_order_id, operator_id, reason_id, start_time, notes),
    )
    conn.commit()
    event_id = cur.lastrowid
    conn.close()
    return event_id

def close_downtime_event(event_id):
    conn = get_connection()
    cur = conn.cursor()
    end_time = datetime.utcnow()
    cur.execute("SELECT start_time FROM downtime_events WHERE id = ?", (event_id,))
    row = cur.fetchone()
    if row:
        start_time = datetime.fromisoformat(row["start_time"])
        duration = (end_time - start_time).total_seconds() / 60.0
        cur.execute(
            "UPDATE downtime_events SET end_time = ?, duration_minutes = ? WHERE id = ?",
            (end_time.isoformat(), duration, event_id),
        )
        conn.commit()
    conn.close()
```

Codex can then:

* Build `Operator_Panel.py` using the DB helpers & `st.session_state`.
* Build dashboard queries using Pandas and streamlit charts.
* Flesh out admin config tables.

---

If you’d like, I can next:

* Draft a **complete `1_Operator_Panel.py`** file with full Streamlit UI, or
* Add a **data seeding script** with example lines/machines/reasons so you can demo immediately.
