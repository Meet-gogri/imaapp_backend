from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import Base, engine
from app.routers import auth, profile, sos, insurance

Base.metadata.create_all(bind=engine)

# One-time-safe schema fix, run automatically on every startup (free tier has
# no Shell/Jobs access, so this replaces needing to run a script manually).
# "IF NOT EXISTS" makes this harmless to run again on every future deploy -
# it does nothing once the columns already exist.
with engine.connect() as _conn:
    for _stmt in [
        "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION",
        "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION",
        "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS profile_complete BOOLEAN DEFAULT FALSE",
    ]:
        try:
            _conn.execute(text(_stmt))
        except Exception as _exc:
            # SQLite doesn't support "IF NOT EXISTS" on ADD COLUMN the same
            # way - if you're on SQLite instead of Postgres, this is safe to
            # ignore as long as the app still starts.
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