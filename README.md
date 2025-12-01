# Digital Andon & Downtime Tracker

A simple, tablet-friendly Streamlit application for tracking manufacturing downtime, quality issues, and production counts. Designed as a starting point for digital transformation on the factory floor, featuring a tiered Lean Management System (SQDC).

## Features

### Operational Tools
- **Operator Panel**:
    - Log downtime events with reasons (Planned/Unplanned).
    - Real-time downtime timer.
    - Log scrap/quality issues and good production counts.
    - View recent activity history.
    - URL parameter support for setting default context (e.g., `?line=Line A&machine=Robot 1`).
- **Maintenance View**:
    - Real-time queue of active/open downtime events.
    - Acknowledge dispatch (timestamps response time).
    - Log resolution notes and close tickets directly.

### Lean Management Dashboards (SQDC)
- **Tier 1: Value Stream SQDC (Supervisor/Team View)**:
    - Daily digital board for **S**afety, **Q**uality, **D**elivery, and **C**ost.
    - Track incidents, First Pass Yield (FPY), Production vs Plan, and Downtime minutes.
    - Visual Green/Red status indicators against targets.
- **Tier 2: Executive Summary (Plant View)**:
    - Aggregated plant-wide status matrix.
    - Identify systemic issues across multiple value streams.
    - Action Item tracking for leadership to assign and resolve high-level blockers.

### Administration
- **Admin Config**:
    - Manage Master Data: Lines, Machines, Operators, Reason Codes, and Targets.

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    cd andon-app
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Running the App

1.  Start the Streamlit server:
    ```bash
    streamlit run app.py
    ```

2.  Open your browser to the URL shown (usually `http://localhost:8501`).
3.  **First Run**: The application will automatically create a SQLite database (`andon.db`) and seed it with sample data (Lines, Machines, Reasons, etc.).

## Project Structure

```text
.
├── app.py                   # Main entry point & landing page
├── config.py                # Configuration (Shifts, DB path)
├── db.py                    # Database helpers & schema definition
├── requirements.txt         # Python dependencies
├── pages/
│   ├── 1_Operator_Panel.py       # Operator interface
│   ├── 2_Supervisor_Dashboard.py # Basic metrics (Legacy)
│   ├── 3_Admin_Config.py         # Master data management
│   ├── 4_Maintenance_View.py     # Maintenance ticket management
│   ├── 5_Value_Stream_SQDC.py    # Tier 1 Lean Dashboard
│   └── 6_Executive_Summary.py    # Tier 2 Plant Dashboard
└── README.md
```

## Database Context

The application currently uses **SQLite** for simplicity and portability. The database file `andon.db` is created in the root directory.

### Key Tables
- `lines`, `machines`, `operators`: Master data for the factory hierarchy.
- `downtime_events`: Logs start/end times, reasons, and resolution notes for downtime.
- `quality_events`: Logs scrap/defect counts and reasons.
- `production_counts`: Logs good part counts.
- `safety_incidents`: Logs safety occurrences for the SQDC board.
- `actions`: Tracks leadership action items and their status (Open/Closed).

### Migrations
Database schema changes are handled in `db.py` inside the `init_db()` function. It checks for the existence of tables and columns (using `PRAGMA table_info`) and applies `CREATE TABLE IF NOT EXISTS` or `ALTER TABLE` commands as needed.

## Connecting to a Real Database (PostgreSQL/MySQL)

To scale this application for production use with multiple concurrent users, you should switch to a robust client-server database like PostgreSQL.

### Steps to Migrate

1.  **Install Database Driver**:
    For PostgreSQL, install `psycopg2-binary`:
    ```bash
    pip install psycopg2-binary
    ```

2.  **Update `db.py` Connection**:
    Replace the SQLite connection logic with a connection to your external database.

    *Current (SQLite):*
    ```python
    def get_connection():
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    ```

    *Proposed (PostgreSQL):*
    ```python
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import os

    def get_connection():
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "andon"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "password")
        )
        return conn
    ```

3.  **Adjust SQL Syntax**:
    - Replace `?` placeholders with `%s` (for psycopg2).
    - Ensure `AUTOINCREMENT` (SQLite) is replaced with `SERIAL` or `IDENTITY` columns in your creation scripts.
    - Note: `db.py` uses raw SQL. For a smoother transition, consider refactoring to use an ORM like **SQLAlchemy** or a query builder.

4.  **Environment Variables**:
    Store your database credentials in environment variables or a `.env` file (using `python-dotenv`) instead of hardcoding them.

## Usage Tips

- **URL Params for Tablets**: You can bookmark specific machine contexts for operators:
  `http://localhost:8501/Operator_Panel?line=Line_A&machine=Conveyor_1&operator=John_Doe`
- **Resetting Data**: To reset the local database, simply delete the `andon.db` file and restart the app; it will re-seed automatically.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
