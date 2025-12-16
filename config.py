import os

# Shift Definitions
# Define shift timings.
# Note: For MVP, we assume shifts are within the same day or handle simple overnight logic if needed.
SHIFTS = {
    "All Day": {"start": "00:00", "end": "23:59"},
    "Shift 1": {"start": "06:00", "end": "14:00"},
    "Shift 2": {"start": "14:00", "end": "22:00"},
    "Shift 3": {"start": "22:00", "end": "06:00"},
}

# Database Settings
# Default to SQLite for local/dev; switch to Lakebase via env.
DB_BACKEND = os.getenv("DB_BACKEND", "sqlite").lower()
DB_NAME = os.getenv("DB_NAME", "andon.db")

# Lakebase / Postgres connection (provided automatically in Databricks Apps)
PG_HOST = os.getenv("PGHOST")
PG_PORT = os.getenv("PGPORT", "5432")
PG_DATABASE = os.getenv("PGDATABASE")
PG_USER = os.getenv("PGUSER")
PG_PASSWORD = os.getenv("PGPASSWORD")
PG_SSLMODE = os.getenv("PGSSLMODE", "require")
PG_APPNAME = os.getenv("PGAPPNAME", "andon-app")

# Grafana Configuration (Default)
GRAFANA_URL = "http://localhost:3000"

