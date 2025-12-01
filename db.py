import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd
from config import DB_NAME

DB_PATH = Path(DB_NAME)

def get_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database with the required tables."""
    conn = get_connection()
    cur = conn.cursor()

    # 3.1 lines
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT
        );
    """)

    # 3.2 machines
    cur.execute("""
        CREATE TABLE IF NOT EXISTS machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            line_id INTEGER,
            description TEXT,
            FOREIGN KEY (line_id) REFERENCES lines(id)
        );
    """)

    # 3.3 operators
    cur.execute("""
        CREATE TABLE IF NOT EXISTS operators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            badge_id TEXT
        );
    """)

    # 3.4 work_orders
    cur.execute("""
        CREATE TABLE IF NOT EXISTS work_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wo_number TEXT NOT NULL,
            part_number TEXT,
            target_quantity INTEGER,
            due_date TEXT,
            line_id INTEGER,
            status TEXT DEFAULT 'Scheduled',
            start_date TEXT,
            completed_date TEXT,
            FOREIGN KEY (line_id) REFERENCES lines(id)
        );
    """)

    # Migration for work_orders status
    cur.execute("PRAGMA table_info(work_orders)")
    wo_columns = [col['name'] for col in cur.fetchall()]
    if 'status' not in wo_columns:
        try:
            cur.execute("ALTER TABLE work_orders ADD COLUMN status TEXT DEFAULT 'Scheduled'")
            cur.execute("ALTER TABLE work_orders ADD COLUMN start_date TEXT")
            cur.execute("ALTER TABLE work_orders ADD COLUMN completed_date TEXT")
        except sqlite3.Error as e:
            print(f"Migration error (work_orders): {e}")

    # 3.5 downtime_reasons
    cur.execute("""
        CREATE TABLE IF NOT EXISTS downtime_reasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT
        );
    """)

    # 3.6 quality_reasons
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quality_reasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT
        );
    """)

    # 3.7 downtime_events
    cur.execute("""
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
            notes TEXT,
            technician_id INTEGER,
            acknowledged_at TEXT,
            resolution_notes TEXT,
            FOREIGN KEY (machine_id) REFERENCES machines(id),
            FOREIGN KEY (line_id) REFERENCES lines(id),
            FOREIGN KEY (work_order_id) REFERENCES work_orders(id),
            FOREIGN KEY (operator_id) REFERENCES operators(id),
            FOREIGN KEY (reason_id) REFERENCES downtime_reasons(id),
            FOREIGN KEY (technician_id) REFERENCES operators(id)
        );
    """)

    # Migration: Check if columns exist (for existing DB)
    cur.execute("PRAGMA table_info(downtime_events)")
    columns = [col['name'] for col in cur.fetchall()]
    
    if 'technician_id' not in columns:
        try:
            cur.execute("ALTER TABLE downtime_events ADD COLUMN technician_id INTEGER REFERENCES operators(id)")
            cur.execute("ALTER TABLE downtime_events ADD COLUMN acknowledged_at TEXT")
            cur.execute("ALTER TABLE downtime_events ADD COLUMN resolution_notes TEXT")
        except sqlite3.Error as e:
             print(f"Migration error (ignored if columns exist): {e}")

    # 3.8 quality_events
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quality_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER,
            line_id INTEGER,
            work_order_id INTEGER,
            operator_id INTEGER,
            reason_id INTEGER,
            quantity INTEGER,
            timestamp TEXT,
            notes TEXT,
            FOREIGN KEY (machine_id) REFERENCES machines(id),
            FOREIGN KEY (line_id) REFERENCES lines(id),
            FOREIGN KEY (work_order_id) REFERENCES work_orders(id),
            FOREIGN KEY (operator_id) REFERENCES operators(id),
            FOREIGN KEY (reason_id) REFERENCES quality_reasons(id)
        );
    """)

    # 3.9 production_counts
    cur.execute("""
        CREATE TABLE IF NOT EXISTS production_counts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER,
            line_id INTEGER,
            work_order_id INTEGER,
            operator_id INTEGER,
            good_quantity INTEGER,
            scrap_quantity INTEGER DEFAULT 0,
            timestamp TEXT,
            FOREIGN KEY (machine_id) REFERENCES machines(id),
            FOREIGN KEY (line_id) REFERENCES lines(id),
            FOREIGN KEY (work_order_id) REFERENCES work_orders(id),
            FOREIGN KEY (operator_id) REFERENCES operators(id)
        );
    """)

    # 3.10 safety_incidents
    cur.execute("""
        CREATE TABLE IF NOT EXISTS safety_incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_id INTEGER,
            date TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY(line_id) REFERENCES lines(id)
        );
    """)

    # 3.11 actions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            line_id INTEGER,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            assigned_to INTEGER,
            status TEXT NOT NULL,
            resolution_notes TEXT,
            FOREIGN KEY(line_id) REFERENCES lines(id),
            FOREIGN KEY(assigned_to) REFERENCES operators(id)
        );
    """)

    # 3.12 targets
    cur.execute("""
        CREATE TABLE IF NOT EXISTS targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_id INTEGER,
            metric_type TEXT NOT NULL,
            target_value REAL,
            FOREIGN KEY(line_id) REFERENCES lines(id),
            UNIQUE(line_id, metric_type)
        );
    """)

    # 3.13 inspection_records
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inspection_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_order_id INTEGER,
            line_id INTEGER,
            inspector_id INTEGER,
            result TEXT NOT NULL, 
            measurements TEXT,
            timestamp TEXT,
            notes TEXT,
            FOREIGN KEY (work_order_id) REFERENCES work_orders(id),
            FOREIGN KEY (line_id) REFERENCES lines(id),
            FOREIGN KEY (inspector_id) REFERENCES operators(id)
        );
    """)

    # 3.14 mrb_items
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mrb_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number TEXT,
            quantity INTEGER,
            reason TEXT,
            status TEXT DEFAULT 'Open',
            disposition TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT,
            quality_event_id INTEGER,
            FOREIGN KEY (quality_event_id) REFERENCES quality_events(id)
        );
    """)

    conn.commit()
    conn.close()

# --- Helper Functions ---

def get_lines():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM lines", conn)
    conn.close()
    return df

def get_machines(line_id=None):
    conn = get_connection()
    query = "SELECT * FROM machines"
    params = []
    if line_id:
        query += " WHERE line_id = ?"
        params.append(line_id)
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def get_operators():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM operators", conn)
    conn.close()
    return df

def get_work_orders(line_id=None, status=None):
    conn = get_connection()
    query = "SELECT * FROM work_orders WHERE 1=1"
    params = []
    if line_id:
        query += " AND line_id = ?"
        params.append(line_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def get_downtime_reasons():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM downtime_reasons", conn)
    conn.close()
    return df

def get_quality_reasons():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM quality_reasons", conn)
    conn.close()
    return df

def create_downtime_event(machine_id, line_id, work_order_id, operator_id, reason_id, notes=""):
    conn = get_connection()
    cur = conn.cursor()
    start_time = datetime.now().isoformat()
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
    end_time = datetime.now()
    
    # Fetch start time to calculate duration
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

def acknowledge_downtime_event(event_id, technician_id):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute(
        "UPDATE downtime_events SET technician_id = ?, acknowledged_at = ? WHERE id = ?",
        (technician_id, now, event_id)
    )
    conn.commit()
    conn.close()

def resolve_downtime_event(event_id, resolution_notes):
    conn = get_connection()
    cur = conn.cursor()
    end_time = datetime.now()
    
    # Fetch start time to calculate duration
    cur.execute("SELECT start_time FROM downtime_events WHERE id = ?", (event_id,))
    row = cur.fetchone()
    
    if row:
        start_time = datetime.fromisoformat(row["start_time"])
        duration = (end_time - start_time).total_seconds() / 60.0
        
        cur.execute(
            "UPDATE downtime_events SET end_time = ?, duration_minutes = ?, resolution_notes = ? WHERE id = ?",
            (end_time.isoformat(), duration, resolution_notes, event_id),
        )
        conn.commit()
    conn.close()

def get_active_maintenance_events():
    conn = get_connection()
    # Get all open events, filtered for maintenance if we had categories, but for now all open events
    # Ideally filtered by "Unplanned" or reasons that need maintenance
    query = """
        SELECT d.*, m.name as machine_name, l.name as line_name, r.description as reason_description, r.code as reason_code,
               o.name as operator_name, t.name as technician_name
        FROM downtime_events d
        JOIN machines m ON d.machine_id = m.id
        JOIN lines l ON d.line_id = l.id
        JOIN downtime_reasons r ON d.reason_id = r.id
        LEFT JOIN operators o ON d.operator_id = o.id
        LEFT JOIN operators t ON d.technician_id = t.id
        WHERE d.end_time IS NULL
        ORDER BY d.start_time ASC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def get_active_downtime_event(machine_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM downtime_events WHERE machine_id = ? AND end_time IS NULL ORDER BY start_time DESC LIMIT 1",
        (machine_id,)
    )
    row = cur.fetchone()
    conn.close()
    return row

def log_quality_event(machine_id, line_id, work_order_id, operator_id, reason_id, quantity, notes=""):
    conn = get_connection()
    cur = conn.cursor()
    timestamp = datetime.now().isoformat()
    cur.execute(
        """
        INSERT INTO quality_events (machine_id, line_id, work_order_id, operator_id, reason_id, quantity, timestamp, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (machine_id, line_id, work_order_id, operator_id, reason_id, quantity, timestamp, notes)
    )
    conn.commit()
    conn.close()

def log_production_count(machine_id, line_id, work_order_id, operator_id, good_quantity, scrap_quantity=0):
    conn = get_connection()
    cur = conn.cursor()
    timestamp = datetime.now().isoformat()
    cur.execute(
        """
        INSERT INTO production_counts (machine_id, line_id, work_order_id, operator_id, good_quantity, scrap_quantity, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (machine_id, line_id, work_order_id, operator_id, good_quantity, scrap_quantity, timestamp)
    )
    conn.commit()
    conn.close()

def get_recent_downtime_events(limit=10, machine_id=None):
    conn = get_connection()
    query = """
        SELECT d.*, r.description as reason_description, o.name as operator_name 
        FROM downtime_events d
        LEFT JOIN downtime_reasons r ON d.reason_id = r.id
        LEFT JOIN operators o ON d.operator_id = o.id
    """
    params = []
    if machine_id:
        query += " WHERE d.machine_id = ?"
        params.append(machine_id)
        
    query += " ORDER BY start_time DESC LIMIT ?"
    params.append(limit)
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def get_recent_quality_events(limit=10, machine_id=None):
    conn = get_connection()
    query = """
        SELECT q.*, r.description as reason_description 
        FROM quality_events q
        LEFT JOIN quality_reasons r ON q.reason_id = r.id
    """
    params = []
    if machine_id:
        query += " WHERE q.machine_id = ?"
        params.append(machine_id)
        
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

# For dashboard: Get downtime within a time window
def get_downtime_summary(start_time_str, end_time_str):
    conn = get_connection()
    # Simple overlap check: event starts before window ends AND event ends after window starts (or is ongoing)
    # For MVP we can just query start_time between window or something simple
    # The requirement says "whose time intersects the window".
    
    query = """
        SELECT d.*, m.name as machine_name, l.name as line_name, r.description as reason_description
        FROM downtime_events d
        JOIN machines m ON d.machine_id = m.id
        JOIN lines l ON d.line_id = l.id
        JOIN downtime_reasons r ON d.reason_id = r.id
        WHERE (d.end_time IS NULL OR d.end_time >= ?) AND d.start_time <= ?
    """
    df = pd.read_sql(query, conn, params=(start_time_str, end_time_str))
    conn.close()
    return df

def get_quality_summary(start_time_str, end_time_str):
    conn = get_connection()
    query = """
        SELECT q.*, m.name as machine_name, l.name as line_name, r.description as reason_description
        FROM quality_events q
        JOIN machines m ON q.machine_id = m.id
        JOIN lines l ON q.line_id = l.id
        JOIN quality_reasons r ON q.reason_id = r.id
        WHERE q.timestamp >= ? AND q.timestamp <= ?
    """
    df = pd.read_sql(query, conn, params=(start_time_str, end_time_str))
    conn.close()
    return df

def get_production_summary(start_time_str, end_time_str):
    conn = get_connection()
    query = """
        SELECT p.*, m.name as machine_name, l.name as line_name
        FROM production_counts p
        JOIN machines m ON p.machine_id = m.id
        JOIN lines l ON p.line_id = l.id
        WHERE p.timestamp >= ? AND p.timestamp <= ?
    """
    df = pd.read_sql(query, conn, params=(start_time_str, end_time_str))
    conn.close()
    return df

def log_safety_incident(line_id, date, description):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO safety_incidents (line_id, date, description) VALUES (?, ?, ?)",
        (line_id, date, description)
    )
    conn.commit()
    conn.close()

def get_safety_incidents(line_id, start_date, end_date):
    conn = get_connection()
    query = "SELECT * FROM safety_incidents WHERE line_id = ? AND date >= ? AND date <= ?"
    df = pd.read_sql(query, conn, params=(line_id, start_date, end_date))
    conn.close()
    return df

def create_action(line_id, category, description, assigned_to):
    conn = get_connection()
    cur = conn.cursor()
    timestamp = datetime.now().isoformat()
    cur.execute(
        """
        INSERT INTO actions (timestamp, line_id, category, description, assigned_to, status)
        VALUES (?, ?, ?, ?, ?, 'open')
        """,
        (timestamp, line_id, category, description, assigned_to)
    )
    conn.commit()
    conn.close()

def get_actions(status=None):
    conn = get_connection()
    query = """
        SELECT a.*, l.name as line_name, o.name as assignee_name 
        FROM actions a
        LEFT JOIN lines l ON a.line_id = l.id
        LEFT JOIN operators o ON a.assigned_to = o.id
    """
    params = []
    if status:
        query += " WHERE a.status = ?"
        params.append(status)
    
    query += " ORDER BY timestamp DESC"
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def close_action(action_id, resolution_notes):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE actions SET status = 'closed', resolution_notes = ? WHERE id = ?",
        (resolution_notes, action_id)
    )
    conn.commit()
    conn.close()

def set_target(line_id, metric_type, value):
    conn = get_connection()
    cur = conn.cursor()
    # Upsert logic (INSERT OR REPLACE)
    cur.execute(
        "INSERT OR REPLACE INTO targets (line_id, metric_type, target_value) VALUES (?, ?, ?)",
        (line_id, metric_type, value)
    )
    conn.commit()
    conn.close()

def get_targets(line_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT metric_type, target_value FROM targets WHERE line_id = ?", (line_id,))
    rows = cur.fetchall()
    conn.close()
    
    # Return a dictionary of targets
    targets = {}
    for row in rows:
        targets[row["metric_type"]] = row["target_value"]
    return targets

def add_line(name, description=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO lines (name, description) VALUES (?, ?)", (name, description))
    conn.commit()
    conn.close()

def add_machine(name, line_id, description=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO machines (name, line_id, description) VALUES (?, ?, ?)", (name, line_id, description))
    conn.commit()
    conn.close()

def add_operator(name, badge_id=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO operators (name, badge_id) VALUES (?, ?)", (name, badge_id))
    conn.commit()
    conn.close()

def add_downtime_reason(code, description, category):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO downtime_reasons (code, description, category) VALUES (?, ?, ?)", (code, description, category))
    conn.commit()
    conn.close()

def create_work_order(wo_number, part_number, target_quantity, due_date, line_id, status="Scheduled"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO work_orders (wo_number, part_number, target_quantity, due_date, line_id, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (wo_number, part_number, target_quantity, due_date, line_id, status)
    )
    conn.commit()
    conn.close()

def update_work_order_status(wo_id, status):
    conn = get_connection()
    cur = conn.cursor()
    update_query = "UPDATE work_orders SET status = ?"
    params = [status]
    
    if status == "Active":
        update_query += ", start_date = ?"
        params.append(datetime.now().isoformat())
    elif status == "Completed":
        update_query += ", completed_date = ?"
        params.append(datetime.now().isoformat())
        
    update_query += " WHERE id = ?"
    params.append(wo_id)
    
    cur.execute(update_query, params)
    conn.commit()
    conn.close()

def get_inspection_records(wo_id=None):
    conn = get_connection()
    query = """
        SELECT i.*, o.name as inspector_name, l.name as line_name, w.wo_number
        FROM inspection_records i
        LEFT JOIN operators o ON i.inspector_id = o.id
        LEFT JOIN lines l ON i.line_id = l.id
        LEFT JOIN work_orders w ON i.work_order_id = w.id
    """
    params = []
    if wo_id:
        query += " WHERE i.work_order_id = ?"
        params.append(wo_id)
        
    query += " ORDER BY i.timestamp DESC"
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def create_inspection_record(work_order_id, line_id, inspector_id, result, measurements="", notes=""):
    conn = get_connection()
    cur = conn.cursor()
    timestamp = datetime.now().isoformat()
    cur.execute(
        """
        INSERT INTO inspection_records (work_order_id, line_id, inspector_id, result, measurements, timestamp, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (work_order_id, line_id, inspector_id, result, measurements, timestamp, notes)
    )
    conn.commit()
    conn.close()

def get_mrb_items(status=None):
    conn = get_connection()
    query = "SELECT * FROM mrb_items"
    params = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def create_mrb_item(part_number, quantity, reason, notes="", quality_event_id=None):
    conn = get_connection()
    cur = conn.cursor()
    created_at = datetime.now().isoformat()
    cur.execute(
        """
        INSERT INTO mrb_items (part_number, quantity, reason, status, notes, created_at, quality_event_id)
        VALUES (?, ?, ?, 'Open', ?, ?, ?)
        """,
        (part_number, quantity, reason, notes, created_at, quality_event_id)
    )
    conn.commit()
    conn.close()

def update_mrb_disposition(item_id, disposition, notes=""):
    conn = get_connection()
    cur = conn.cursor()
    updated_at = datetime.now().isoformat()
    cur.execute(
        """
        UPDATE mrb_items 
        SET status = 'Dispositioned', disposition = ?, notes = ?, updated_at = ?
        WHERE id = ?
        """,
        (disposition, notes, updated_at, item_id)
    )
    conn.commit()
    conn.close()

def seed_db():
    """Populates the database with initial sample data."""
    conn = get_connection()
    cur = conn.cursor()

    # Check if lines exist
    cur.execute("SELECT COUNT(*) FROM lines")
    if cur.fetchone()[0] > 0:
        conn.close()
        return

    # Lines
    lines = [
        ("Line_A", "Main Assembly Line"),
        ("Line_B", "Packaging Line"),
    ]
    cur.executemany("INSERT INTO lines (name, description) VALUES (?, ?)", lines)
    
    conn.commit()
    
    # Get Line IDs
    cur.execute("SELECT id, name FROM lines")
    line_map = {row["name"]: row["id"] for row in cur.fetchall()}

    # Machines
    machines = [
        ("Conveyor_1", line_map["Line_A"], "Infeed Conveyor"),
        ("Robot_Arm_1", line_map["Line_A"], "Assembly Robot"),
        ("Packer_1", line_map["Line_B"], "Box Packer"),
    ]
    cur.executemany("INSERT INTO machines (name, line_id, description) VALUES (?, ?, ?)", machines)

    # Operators
    operators = [
        ("John_Doe", "OP001"),
        ("Jane_Smith", "OP002"),
        ("Mike_Johnson", "OP003"),
    ]
    cur.executemany("INSERT INTO operators (name, badge_id) VALUES (?, ?)", operators)

    # Work Orders
    work_orders = [
        ("WO-1001", "PN-A001", 500, "2023-12-31", line_map["Line_A"]),
        ("WO-1002", "PN-B002", 1000, "2023-12-31", line_map["Line_B"]),
    ]
    cur.executemany("INSERT INTO work_orders (wo_number, part_number, target_quantity, due_date, line_id) VALUES (?, ?, ?, ?, ?)", work_orders)

    # Downtime Reasons
    dt_reasons = [
        ("NO_MAT", "No Material", "Unplanned"),
        ("JAM", "Machine Jam", "Unplanned"),
        ("MECH", "Mechanical Failure", "Unplanned"),
        ("BRK", "Break", "Planned"),
        ("CHG", "Changeover", "Planned"),
    ]
    cur.executemany("INSERT INTO downtime_reasons (code, description, category) VALUES (?, ?, ?)", dt_reasons)

    # Quality Reasons
    q_reasons = [
        ("DIM", "Dimension Out of Spec", "Defect"),
        ("SCR", "Scratch/Dent", "Defect"),
        ("MAT", "Material Defect", "Defect"),
        ("REW", "Rework", "Rework"),
    ]
    cur.executemany("INSERT INTO quality_reasons (code, description, category) VALUES (?, ?, ?)", q_reasons)

    conn.commit()
    conn.close()
