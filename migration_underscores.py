import sqlite3
from config import DB_NAME

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

# Normalize names: Replace spaces with underscores
tables = {
    "lines": "name",
    "machines": "name",
    "operators": "name"
}

for table, col in tables.items():
    cur.execute(f"SELECT id, {col} FROM {table}")
    rows = cur.fetchall()
    for row in rows:
        row_id = row[0]
        old_val = row[1]
        if " " in old_val:
            new_val = old_val.replace(" ", "_")
            print(f"Updating {table}: {old_val} -> {new_val}")
            cur.execute(f"UPDATE {table} SET {col} = ? WHERE id = ?", (new_val, row_id))

conn.commit()
conn.close()

