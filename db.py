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
            FOREIGN KEY (line_id) REFERENCES lines(id)
        );
    """)

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

def get_work_orders(line_id=None):
    conn = get_connection()
    query = "SELECT * FROM work_orders"
    params = []
    if line_id:
        query += " WHERE line_id = ?"
        params.append(line_id)
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
        ("Line A", "Main Assembly Line"),
        ("Line B", "Packaging Line"),
    ]
    cur.executemany("INSERT INTO lines (name, description) VALUES (?, ?)", lines)
    
    conn.commit()
    
    # Get Line IDs
    cur.execute("SELECT id, name FROM lines")
    line_map = {row["name"]: row["id"] for row in cur.fetchall()}

    # Machines
    machines = [
        ("Conveyor 1", line_map["Line A"], "Infeed Conveyor"),
        ("Robot Arm 1", line_map["Line A"], "Assembly Robot"),
        ("Packer 1", line_map["Line B"], "Box Packer"),
    ]
    cur.executemany("INSERT INTO machines (name, line_id, description) VALUES (?, ?, ?)", machines)

    # Operators
    operators = [
        ("John Doe", "OP001"),
        ("Jane Smith", "OP002"),
        ("Mike Johnson", "OP003"),
    ]
    cur.executemany("INSERT INTO operators (name, badge_id) VALUES (?, ?)", operators)

    # Work Orders
    work_orders = [
        ("WO-1001", "PN-A001", 500, "2023-12-31", line_map["Line A"]),
        ("WO-1002", "PN-B002", 1000, "2023-12-31", line_map["Line B"]),
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
