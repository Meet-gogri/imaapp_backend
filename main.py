from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, profile, sos, insurance

Base.metadata.create_all(bind=engine)

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
