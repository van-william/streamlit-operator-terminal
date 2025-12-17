import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Any, Iterable, Optional

import pandas as pd

from config import (
    ANDON_SCHEMA,
    DB_BACKEND,
    DB_NAME,
    PG_APPNAME,
    PG_DATABASE,
    PG_HOST,
    PG_PORT,
    PG_SSLMODE,
    PG_USER,
)

# Optional import for Lakebase (PostgreSQL)
try:
    import psycopg2
    import psycopg2.extras
except ImportError:  # pragma: no cover - handled at runtime if missing
    psycopg2 = None

# Optional import for Databricks SDK (used for token-based Lakebase auth)
try:
    from databricks.sdk import WorkspaceClient
except ImportError:  # pragma: no cover
    WorkspaceClient = None

DB_PATH = Path(DB_NAME)
IS_LAKEBASE = DB_BACKEND == "lakebase"


def _cursor_factory():
    if IS_LAKEBASE and psycopg2:
        return psycopg2.extras.RealDictCursor
    return None


def _lakebase_password():
    """
    Resolve password for Lakebase using Databricks OAuth token.
    PGPASSWORD is intentionally not used; we rely on token auth.
    """
    if WorkspaceClient is None:
        raise RuntimeError("databricks-sdk is required for Lakebase token authentication.")
    client = WorkspaceClient()
    return client.config.oauth_token().access_token


def _ensure_schema(conn):
    """Create and set search_path to the configured schema for Lakebase."""
    if not IS_LAKEBASE or not ANDON_SCHEMA:
        return
    with conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{ANDON_SCHEMA}"')
        cur.execute(f'SET search_path TO "{ANDON_SCHEMA}"')


def get_connection():
    """Establishes a connection to the configured database."""
    if IS_LAKEBASE:
        if psycopg2 is None:
            raise RuntimeError("psycopg2-binary is required for Lakebase support.")
        required = {
            "PGHOST": PG_HOST,
            "PGPORT": PG_PORT,
            "PGDATABASE": PG_DATABASE,
            "PGUSER": PG_USER,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(f"Missing Lakebase environment variables: {', '.join(missing)}")
        password = _lakebase_password()
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            dbname=PG_DATABASE,
            user=PG_USER,
            password=password,
            sslmode=PG_SSLMODE,
            application_name=PG_APPNAME,
        )
        _ensure_schema(conn)
        return conn

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _prepare_query(query: str) -> str:
    """Adjust placeholder style for the active backend."""
    if IS_LAKEBASE:
        return query.replace("?", "%s")
    return query


def _normalize_params(params: Optional[Iterable[Any]]) -> list:
    """Convert numpy/pandas scalar types to native Python scalars for DB adapters."""
    if params is None:
        return []
    normalized = []
    for value in params:
        if hasattr(value, "item"):
            try:
                value = value.item()
            except Exception:  # noqa: BLE001 - best-effort fallback
                pass
        normalized.append(value)
    return normalized


def _read_df(query: str, params: Optional[Iterable[Any]] = None) -> pd.DataFrame:
    conn = get_connection()
    sql = _prepare_query(query)
    df = pd.read_sql(sql, conn, params=_normalize_params(params))
    conn.close()
    return df


def _fetch_one(query: str, params: Optional[Iterable[Any]] = None):
    conn = get_connection()
    cursor_kwargs = {}
    factory = _cursor_factory()
    if factory:
        cursor_kwargs["cursor_factory"] = factory
    cur = conn.cursor(**cursor_kwargs)
    cur.execute(_prepare_query(query), _normalize_params(params))
    row = cur.fetchone()
    conn.close()
    return row


def _execute(query: str, params: Optional[Iterable[Any]] = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(_prepare_query(query), _normalize_params(params))
    conn.commit()
    conn.close()


def _execute_returning_id(query: str, params: Optional[Iterable[Any]] = None) -> Any:
    conn = get_connection()
    cursor_kwargs = {}
    factory = _cursor_factory()
    if factory:
        cursor_kwargs["cursor_factory"] = factory
    cur = conn.cursor(**cursor_kwargs)

    sql = _prepare_query(query)
    if IS_LAKEBASE and "returning" not in sql.lower():
        sql = sql.rstrip().rstrip(";") + " RETURNING id"

    cur.execute(sql, _normalize_params(params))
    if IS_LAKEBASE:
        row = cur.fetchone()
        if isinstance(row, dict):
            new_id = row.get("id") or list(row.values())[0]
        else:
            new_id = row[0]
    else:
        new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id


def _executemany(query: str, seq_of_params: Iterable[Iterable[Any]]):
    conn = get_connection()
    cur = conn.cursor()
    normalized = [_normalize_params(params) for params in seq_of_params]
    cur.executemany(_prepare_query(query), normalized)
    conn.commit()
    conn.close()


def _get_columns(cur, table_name: str):
    if IS_LAKEBASE:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema() AND table_name = %s
            """,
            (table_name,),
        )
        return [row["column_name"] if isinstance(row, dict) else row[0] for row in cur.fetchall()]
    else:
        cur.execute(f"PRAGMA table_info({table_name})")
        return [row["name"] for row in cur.fetchall()]

def init_db():
    """Initializes the database with the required tables."""
    conn = get_connection()
    cursor_kwargs = {}
    factory = _cursor_factory()
    if factory:
        cursor_kwargs["cursor_factory"] = factory
    cur = conn.cursor(**cursor_kwargs)

    pk_type = "SERIAL PRIMARY KEY" if IS_LAKEBASE else "INTEGER PRIMARY KEY AUTOINCREMENT"

    # 3.1 lines
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lines (
            id {pk_type},
            name TEXT NOT NULL,
            description TEXT
        );
    """)

    # 3.2 machines
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS machines (
            id {pk_type},
            name TEXT NOT NULL,
            line_id INTEGER,
            description TEXT,
            FOREIGN KEY (line_id) REFERENCES lines(id)
        );
    """)

    # 3.3 operators
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS operators (
            id {pk_type},
            name TEXT NOT NULL,
            badge_id TEXT
        );
    """)

    # 3.4 work_orders
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS work_orders (
            id {pk_type},
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
    wo_columns = _get_columns(cur, "work_orders")
    if "status" not in wo_columns:
        try:
            cur.execute("ALTER TABLE work_orders ADD COLUMN status TEXT DEFAULT 'Scheduled'")
            cur.execute("ALTER TABLE work_orders ADD COLUMN start_date TEXT")
            cur.execute("ALTER TABLE work_orders ADD COLUMN completed_date TEXT")
        except Exception as e:  # noqa: BLE001
            print(f"Migration error (work_orders): {e}")

    # 3.5 downtime_reasons
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS downtime_reasons (
            id {pk_type},
            code TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT
        );
    """)

    # 3.6 quality_reasons
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS quality_reasons (
            id {pk_type},
            code TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT
        );
    """)

    # 3.7 downtime_events
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS downtime_events (
            id {pk_type},
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
    columns = _get_columns(cur, "downtime_events")

    if "technician_id" not in columns:
        try:
            cur.execute("ALTER TABLE downtime_events ADD COLUMN technician_id INTEGER REFERENCES operators(id)")
            cur.execute("ALTER TABLE downtime_events ADD COLUMN acknowledged_at TEXT")
            cur.execute("ALTER TABLE downtime_events ADD COLUMN resolution_notes TEXT")
        except Exception as e:  # noqa: BLE001
            print(f"Migration error (ignored if columns exist): {e}")

    # 3.8 quality_events
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS quality_events (
            id {pk_type},
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
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS production_counts (
            id {pk_type},
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
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS safety_incidents (
            id {pk_type},
            line_id INTEGER,
            date TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY(line_id) REFERENCES lines(id)
        );
    """)

    # 3.11 actions
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS actions (
            id {pk_type},
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
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS targets (
            id {pk_type},
            line_id INTEGER,
            metric_type TEXT NOT NULL,
            target_value REAL,
            FOREIGN KEY(line_id) REFERENCES lines(id),
            UNIQUE(line_id, metric_type)
        );
    """)

    # 3.13 inspection_records
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS inspection_records (
            id {pk_type},
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
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS mrb_items (
            id {pk_type},
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
    return _read_df("SELECT * FROM lines")

def get_machines(line_id=None):
    query = "SELECT * FROM machines"
    params = []
    if line_id:
        query += " WHERE line_id = ?"
        params.append(line_id)
    return _read_df(query, params=params)

def get_operators():
    return _read_df("SELECT * FROM operators")

def get_work_orders(line_id=None, status=None):
    query = "SELECT * FROM work_orders WHERE 1=1"
    params = []
    if line_id:
        query += " AND line_id = ?"
        params.append(line_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    return _read_df(query, params=params)

def get_downtime_reasons():
    return _read_df("SELECT * FROM downtime_reasons")

def get_quality_reasons():
    return _read_df("SELECT * FROM quality_reasons")

def create_downtime_event(machine_id, line_id, work_order_id, operator_id, reason_id, notes=""):
    start_time = datetime.now().isoformat()
    return _execute_returning_id(
        """
        INSERT INTO downtime_events (machine_id, line_id, work_order_id, operator_id, reason_id, start_time, end_time, duration_minutes, notes)
        VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?)
        """,
        (machine_id, line_id, work_order_id, operator_id, reason_id, start_time, notes),
    )

def close_downtime_event(event_id):
    end_time = datetime.now()
    
    # Fetch start time to calculate duration
    row = _fetch_one("SELECT start_time FROM downtime_events WHERE id = ?", (event_id,))
    
    if row:
        start_time = datetime.fromisoformat(row["start_time"])
        duration = (end_time - start_time).total_seconds() / 60.0
        
        _execute(
            "UPDATE downtime_events SET end_time = ?, duration_minutes = ? WHERE id = ?",
            (end_time.isoformat(), duration, event_id),
        )

def acknowledge_downtime_event(event_id, technician_id):
    now = datetime.now().isoformat()
    _execute(
        "UPDATE downtime_events SET technician_id = ?, acknowledged_at = ? WHERE id = ?",
        (technician_id, now, event_id)
    )

def resolve_downtime_event(event_id, resolution_notes):
    end_time = datetime.now()
    
    # Fetch start time to calculate duration
    row = _fetch_one("SELECT start_time FROM downtime_events WHERE id = ?", (event_id,))
    
    if row:
        start_time = datetime.fromisoformat(row["start_time"])
        duration = (end_time - start_time).total_seconds() / 60.0
        
        _execute(
            "UPDATE downtime_events SET end_time = ?, duration_minutes = ?, resolution_notes = ? WHERE id = ?",
            (end_time.isoformat(), duration, resolution_notes, event_id),
        )

def get_active_maintenance_events():
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
    return _read_df(query)

def get_active_downtime_event(machine_id):
    return _fetch_one(
        "SELECT * FROM downtime_events WHERE machine_id = ? AND end_time IS NULL ORDER BY start_time DESC LIMIT 1",
        (machine_id,)
    )

def log_quality_event(machine_id, line_id, work_order_id, operator_id, reason_id, quantity, notes=""):
    timestamp = datetime.now().isoformat()
    _execute(
        """
        INSERT INTO quality_events (machine_id, line_id, work_order_id, operator_id, reason_id, quantity, timestamp, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (machine_id, line_id, work_order_id, operator_id, reason_id, quantity, timestamp, notes)
    )

def log_production_count(machine_id, line_id, work_order_id, operator_id, good_quantity, scrap_quantity=0):
    timestamp = datetime.now().isoformat()
    _execute(
        """
        INSERT INTO production_counts (machine_id, line_id, work_order_id, operator_id, good_quantity, scrap_quantity, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (machine_id, line_id, work_order_id, operator_id, good_quantity, scrap_quantity, timestamp)
    )

def get_recent_downtime_events(limit=10, machine_id=None):
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
    
    return _read_df(query, params=params)

def get_recent_quality_events(limit=10, machine_id=None):
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
    
    return _read_df(query, params=params)

# For dashboard: Get downtime within a time window
def get_downtime_summary(start_time_str, end_time_str):
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
    return _read_df(query, params=(start_time_str, end_time_str))

def get_quality_summary(start_time_str, end_time_str):
    query = """
        SELECT q.*, m.name as machine_name, l.name as line_name, r.description as reason_description
        FROM quality_events q
        JOIN machines m ON q.machine_id = m.id
        JOIN lines l ON q.line_id = l.id
        JOIN quality_reasons r ON q.reason_id = r.id
        WHERE q.timestamp >= ? AND q.timestamp <= ?
    """
    return _read_df(query, params=(start_time_str, end_time_str))

def get_production_summary(start_time_str, end_time_str):
    query = """
        SELECT p.*, m.name as machine_name, l.name as line_name
        FROM production_counts p
        JOIN machines m ON p.machine_id = m.id
        JOIN lines l ON p.line_id = l.id
        WHERE p.timestamp >= ? AND p.timestamp <= ?
    """
    return _read_df(query, params=(start_time_str, end_time_str))

def log_safety_incident(line_id, date, description):
    _execute(
        "INSERT INTO safety_incidents (line_id, date, description) VALUES (?, ?, ?)",
        (line_id, date, description)
    )

def get_safety_incidents(line_id, start_date, end_date):
    query = "SELECT * FROM safety_incidents WHERE line_id = ? AND date >= ? AND date <= ?"
    return _read_df(query, params=(line_id, start_date, end_date))

def create_action(line_id, category, description, assigned_to):
    timestamp = datetime.now().isoformat()
    _execute(
        """
        INSERT INTO actions (timestamp, line_id, category, description, assigned_to, status)
        VALUES (?, ?, ?, ?, ?, 'open')
        """,
        (timestamp, line_id, category, description, assigned_to)
    )

def get_actions(status=None):
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
    
    return _read_df(query, params=params)

def close_action(action_id, resolution_notes):
    _execute(
        "UPDATE actions SET status = 'closed', resolution_notes = ? WHERE id = ?",
        (resolution_notes, action_id)
    )

def set_target(line_id, metric_type, value):
    if IS_LAKEBASE:
        _execute(
            """
            INSERT INTO targets (line_id, metric_type, target_value)
            VALUES (?, ?, ?)
            ON CONFLICT (line_id, metric_type) DO UPDATE SET target_value = EXCLUDED.target_value
            """,
            (line_id, metric_type, value),
        )
    else:
        _execute(
            "INSERT OR REPLACE INTO targets (line_id, metric_type, target_value) VALUES (?, ?, ?)",
            (line_id, metric_type, value),
        )

def get_targets(line_id):
    rows = _read_df("SELECT metric_type, target_value FROM targets WHERE line_id = ?", params=(line_id,))
    targets = {}
    for _, row in rows.iterrows():
        targets[row["metric_type"]] = row["target_value"]
    return targets

def add_line(name, description=""):
    _execute("INSERT INTO lines (name, description) VALUES (?, ?)", (name, description))

def add_machine(name, line_id, description=""):
    _execute("INSERT INTO machines (name, line_id, description) VALUES (?, ?, ?)", (name, line_id, description))

def add_operator(name, badge_id=""):
    _execute("INSERT INTO operators (name, badge_id) VALUES (?, ?)", (name, badge_id))

def add_downtime_reason(code, description, category):
    _execute("INSERT INTO downtime_reasons (code, description, category) VALUES (?, ?, ?)", (code, description, category))

def create_work_order(wo_number, part_number, target_quantity, due_date, line_id, status="Scheduled"):
    _execute(
        """
        INSERT INTO work_orders (wo_number, part_number, target_quantity, due_date, line_id, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (wo_number, part_number, target_quantity, due_date, line_id, status)
    )

def update_work_order_status(wo_id, status):
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
    
    _execute(update_query, params)

def get_inspection_records(wo_id=None):
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
    return _read_df(query, params=params)

def create_inspection_record(work_order_id, line_id, inspector_id, result, measurements="", notes=""):
    timestamp = datetime.now().isoformat()
    _execute(
        """
        INSERT INTO inspection_records (work_order_id, line_id, inspector_id, result, measurements, timestamp, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (work_order_id, line_id, inspector_id, result, measurements, timestamp, notes)
    )

def get_mrb_items(status=None):
    query = "SELECT * FROM mrb_items"
    params = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    return _read_df(query, params=params)

def create_mrb_item(part_number, quantity, reason, notes="", quality_event_id=None):
    created_at = datetime.now().isoformat()
    _execute(
        """
        INSERT INTO mrb_items (part_number, quantity, reason, status, notes, created_at, quality_event_id)
        VALUES (?, ?, ?, 'Open', ?, ?, ?)
        """,
        (part_number, quantity, reason, notes, created_at, quality_event_id)
    )

def update_mrb_disposition(item_id, disposition, notes=""):
    updated_at = datetime.now().isoformat()
    _execute(
        """
        UPDATE mrb_items 
        SET status = 'Dispositioned', disposition = ?, notes = ?, updated_at = ?
        WHERE id = ?
        """,
        (disposition, notes, updated_at, item_id)
    )

def seed_db():
    """Populates the database with initial sample data."""
    conn = get_connection()
    cursor_kwargs = {}
    factory = _cursor_factory()
    if factory:
        cursor_kwargs["cursor_factory"] = factory
    cur = conn.cursor(**cursor_kwargs)

    # Check if lines exist
    cur.execute(_prepare_query("SELECT COUNT(*) as cnt FROM lines"))
    existing = cur.fetchone()
    existing_count = existing["cnt"] if isinstance(existing, dict) else existing[0]
    if existing_count > 0:
        conn.close()
        return

    # Lines
    lines = [
        ("Line_A", "Main Assembly Line"),
        ("Line_B", "Packaging Line"),
    ]
    cur.executemany(_prepare_query("INSERT INTO lines (name, description) VALUES (?, ?)"), lines)
    
    conn.commit()
    
    # Get Line IDs
    cur.execute("SELECT id, name FROM lines")
    line_map = {}
    for row in cur.fetchall():
        line_map[row["name"]] = row["id"]

    # Machines
    machines = [
        ("Conveyor_1", line_map["Line_A"], "Infeed Conveyor"),
        ("Robot_Arm_1", line_map["Line_A"], "Assembly Robot"),
        ("Packer_1", line_map["Line_B"], "Box Packer"),
    ]
    cur.executemany(_prepare_query("INSERT INTO machines (name, line_id, description) VALUES (?, ?, ?)"), machines)

    # Operators
    operators = [
        ("John_Doe", "OP001"),
        ("Jane_Smith", "OP002"),
        ("Mike_Johnson", "OP003"),
    ]
    cur.executemany(_prepare_query("INSERT INTO operators (name, badge_id) VALUES (?, ?)"), operators)

    # Work Orders
    work_orders = [
        ("WO-1001", "PN-A001", 500, "2023-12-31", line_map["Line_A"]),
        ("WO-1002", "PN-B002", 1000, "2023-12-31", line_map["Line_B"]),
    ]
    cur.executemany(_prepare_query("INSERT INTO work_orders (wo_number, part_number, target_quantity, due_date, line_id) VALUES (?, ?, ?, ?, ?)"), work_orders)

    # Downtime Reasons
    dt_reasons = [
        ("NO_MAT", "No Material", "Unplanned"),
        ("JAM", "Machine Jam", "Unplanned"),
        ("MECH", "Mechanical Failure", "Unplanned"),
        ("BRK", "Break", "Planned"),
        ("CHG", "Changeover", "Planned"),
    ]
    cur.executemany(_prepare_query("INSERT INTO downtime_reasons (code, description, category) VALUES (?, ?, ?)"), dt_reasons)

    # Quality Reasons
    q_reasons = [
        ("DIM", "Dimension Out of Spec", "Defect"),
        ("SCR", "Scratch/Dent", "Defect"),
        ("MAT", "Material Defect", "Defect"),
        ("REW", "Rework", "Rework"),
    ]
    cur.executemany(_prepare_query("INSERT INTO quality_reasons (code, description, category) VALUES (?, ?, ?)"), q_reasons)

    conn.commit()
    conn.close()
