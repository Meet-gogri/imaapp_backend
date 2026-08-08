"""
One-time fix: adds the columns the new code expects (latitude, longitude,
profile_complete) to your EXISTING doctors table, and creates the new
otp_codes / sos_alerts / sos_recipients tables - all without touching any
data already in the doctors table.

Run this once, from Render's Shell tab (or locally if DATABASE_URL in your
.env points at the same database):

    python migrate_add_location_columns.py
"""
from sqlalchemy import text
from app.database import engine, Base
from app import models  # noqa: F401 - needed so Base knows about the new tables

STATEMENTS = [
    "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION",
    "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION",
    "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS profile_complete BOOLEAN DEFAULT FALSE",
]

with engine.connect() as conn:
    for stmt in STATEMENTS:
        print("Running:", stmt)
        conn.execute(text(stmt))
    conn.commit()

print("Columns added. Now creating any missing tables (otp_codes, sos_alerts, sos_recipients)...")
Base.metadata.create_all(bind=engine)
print("Done. Your existing doctor records are untouched - they just have the new columns now (empty until each doctor re-saves their profile).")