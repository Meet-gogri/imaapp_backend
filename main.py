from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import os

from app.database import Base, engine
from app.routers import auth, profile, sos, insurance

# ---------------------------------------------------------------------------
# DATABASE RESET SWITCH (guaranteed schema fix)
#
# Set RESET_DB=true on Render's Environment tab, push this file, let it
# redeploy once - this drops and recreates every table fresh with the
# correct, current schema. Since only test data exists right now, this is
# safe. AFTER you confirm sign-in works again, go back to Render and set
# RESET_DB=false (or delete the variable) - otherwise every future deploy
# will wipe real doctor registrations once you have them.
# ---------------------------------------------------------------------------
if os.getenv("RESET_DB", "false").lower() == "true":
    print("[RESET_DB=true] Dropping and recreating all tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("[RESET_DB=true] Done - all tables rebuilt fresh.")
else:
    Base.metadata.create_all(bind=engine)
    # Gentler fallback for when you don't want to wipe data: try adding just
    # the missing columns. Harmless to run every startup.
    with engine.connect() as _conn:
        for _stmt in [
            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION",
            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION",
            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS profile_complete BOOLEAN DEFAULT FALSE",
        ]:
            try:
                _conn.execute(text(_stmt))
            except Exception as _exc:
                print(f"[startup migration] skipped: {_stmt} ({_exc})")
        _conn.commit()

app = FastAPI(title="PolicyEra IMA Portal Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for a member-app demo; tighten to your app's origin(s) before wider release
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(sos.router)
app.include_router(insurance.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to PolicyEra IMA Portal Backend API", "version": "2.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/debug/schema-check")
def schema_check():
    """Temporary diagnostic - shows exactly what columns the live database
    actually has right now, no guessing from logs. Visit this URL directly
    in a browser. Remove this endpoint once the schema issue is confirmed
    fixed - it's not meant to stay in a production app."""
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'doctors' ORDER BY column_name"
        ))
        columns = [row[0] for row in result]
    return {
        "doctors_table_columns": columns,
        "has_latitude": "latitude" in columns,
        "has_longitude": "longitude" in columns,
        "has_profile_complete": "profile_complete" in columns,
    }