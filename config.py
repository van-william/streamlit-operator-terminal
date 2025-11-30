# Shift Definitions
# Define shift timings.
# Note: For MVP, we assume shifts are within the same day or handle simple overnight logic if needed.
SHIFTS = {
    "All Day": {"start": "00:00", "end": "23:59"},
    "Shift 1": {"start": "06:00", "end": "14:00"},
    "Shift 2": {"start": "14:00", "end": "22:00"},
    "Shift 3": {"start": "22:00", "end": "06:00"},
}

# Database Path
DB_NAME = "andon.db"

