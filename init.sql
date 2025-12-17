-- Andon Lakebase bootstrap script
-- Creates schema, tables, optional seed rows, and grants for the app principal.
-- Replace <CLIENT_ID> with your Databricks App client ID when running grants.

-- 1) Schema (adjust if you prefer a different name)
CREATE SCHEMA IF NOT EXISTS andon;
SET search_path TO andon;

-- 2) Tables (SERIAL PKs for Lakebase/Postgres)
CREATE TABLE IF NOT EXISTS lines (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT
);

CREATE TABLE IF NOT EXISTS machines (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  line_id INTEGER,
  description TEXT,
  FOREIGN KEY (line_id) REFERENCES lines(id)
);

CREATE TABLE IF NOT EXISTS operators (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  badge_id TEXT
);

CREATE TABLE IF NOT EXISTS work_orders (
  id SERIAL PRIMARY KEY,
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

CREATE TABLE IF NOT EXISTS downtime_reasons (
  id SERIAL PRIMARY KEY,
  code TEXT NOT NULL,
  description TEXT NOT NULL,
  category TEXT
);

CREATE TABLE IF NOT EXISTS quality_reasons (
  id SERIAL PRIMARY KEY,
  code TEXT NOT NULL,
  description TEXT NOT NULL,
  category TEXT
);

CREATE TABLE IF NOT EXISTS downtime_events (
  id SERIAL PRIMARY KEY,
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

CREATE TABLE IF NOT EXISTS quality_events (
  id SERIAL PRIMARY KEY,
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

CREATE TABLE IF NOT EXISTS production_counts (
  id SERIAL PRIMARY KEY,
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

CREATE TABLE IF NOT EXISTS safety_incidents (
  id SERIAL PRIMARY KEY,
  line_id INTEGER,
  date TEXT NOT NULL,
  description TEXT,
  FOREIGN KEY (line_id) REFERENCES lines(id)
);

CREATE TABLE IF NOT EXISTS actions (
  id SERIAL PRIMARY KEY,
  timestamp TEXT NOT NULL,
  line_id INTEGER,
  category TEXT NOT NULL,
  description TEXT NOT NULL,
  assigned_to INTEGER,
  status TEXT NOT NULL,
  resolution_notes TEXT,
  FOREIGN KEY (line_id) REFERENCES lines(id),
  FOREIGN KEY (assigned_to) REFERENCES operators(id)
);

CREATE TABLE IF NOT EXISTS targets (
  id SERIAL PRIMARY KEY,
  line_id INTEGER,
  metric_type TEXT NOT NULL,
  target_value REAL,
  FOREIGN KEY (line_id) REFERENCES lines(id),
  UNIQUE (line_id, metric_type)
);

CREATE TABLE IF NOT EXISTS inspection_records (
  id SERIAL PRIMARY KEY,
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

CREATE TABLE IF NOT EXISTS mrb_items (
  id SERIAL PRIMARY KEY,
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

-- 3) Optional seed data (safe to rerun; duplicates possible if re-run as-is)
INSERT INTO lines (name, description) VALUES
  ('Line_A', 'Main Assembly Line'),
  ('Line_B', 'Packaging Line')
ON CONFLICT DO NOTHING;

INSERT INTO machines (name, line_id, description)
SELECT * FROM (
  VALUES
    ('Conveyor_1', (SELECT id FROM lines WHERE name = 'Line_A'), 'Infeed Conveyor'),
    ('Robot_Arm_1', (SELECT id FROM lines WHERE name = 'Line_A'), 'Assembly Robot'),
    ('Packer_1',    (SELECT id FROM lines WHERE name = 'Line_B'), 'Box Packer')
) AS v(name, line_id, description)
ON CONFLICT DO NOTHING;

INSERT INTO operators (name, badge_id) VALUES
  ('John_Doe', 'OP001'),
  ('Jane_Smith', 'OP002'),
  ('Mike_Johnson', 'OP003')
ON CONFLICT DO NOTHING;

INSERT INTO downtime_reasons (code, description, category) VALUES
  ('NO_MAT', 'No Material', 'Unplanned'),
  ('JAM', 'Machine Jam', 'Unplanned'),
  ('MECH', 'Mechanical Failure', 'Unplanned'),
  ('BRK', 'Break', 'Planned'),
  ('CHG', 'Changeover', 'Planned')
ON CONFLICT DO NOTHING;

INSERT INTO quality_reasons (code, description, category) VALUES
  ('DIM', 'Dimension Out of Spec', 'Defect'),
  ('SCR', 'Scratch/Dent', 'Defect'),
  ('MAT', 'Material Defect', 'Defect'),
  ('REW', 'Rework', 'Rework')
ON CONFLICT DO NOTHING;

INSERT INTO work_orders (wo_number, part_number, target_quantity, due_date, line_id) VALUES
  ('WO-1001', 'PN-A001', 500, '2023-12-31', (SELECT id FROM lines WHERE name = 'Line_A')),
  ('WO-1002', 'PN-B002', 1000, '2023-12-31', (SELECT id FROM lines WHERE name = 'Line_B'))
ON CONFLICT DO NOTHING;

-- 4) Grants (replace <CLIENT_ID> with your app principal)
GRANT USAGE ON SCHEMA andon TO "<CLIENT_ID>";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA andon TO "<CLIENT_ID>";
ALTER DEFAULT PRIVILEGES IN SCHEMA andon GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "<CLIENT_ID>";

