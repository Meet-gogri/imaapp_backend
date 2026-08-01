import os
from dotenv import load_dotenv

# 1. MUST BE CALLED BEFORE os.getenv() to load the .env file variables
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List, Optional

# 2. Get DATABASE_URL (Uses .env value or falls back to '12345' as default)
# Loads variables from your local .env file
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set in .env file!")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI(
    title="IMA Doctor Portal Backend API",
    description="Microservices powering Announcements, Member Directory, and 10km SOS System",
    version="1.0.0"
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Request & Response Schemas
class SOSPayload(BaseModel):
    doctor_id: str
    latitude: float
    longitude: float

class AnnouncementResponse(BaseModel):
    id: str
    title: str
    academic_year: str
    pdf_url: Optional[str] = None

# API Endpoints
@app.get("/")
def root():
    return {"status": "SUCCESS", "message": "IMA FastAPI Backend running cleanly on 'imaapp' database!"}

# Endpoint 1: Fetch Year-wise Announcements
@app.get("/api/v1/announcements", response_model=List[AnnouncementResponse])
def get_announcements(db: Session = Depends(get_db)):
    try:
        query = text("SELECT id, title, academic_year, pdf_url FROM announcements ORDER BY posted_date DESC;")
        results = db.execute(query).fetchall()
        
        return [
            {
                "id": str(row.id),
                "title": str(row.title),
                "academic_year": str(row.academic_year),
                "pdf_url": row.pdf_url if row.pdf_url else None
            }
            for row in results
        ]
    except Exception as e:
        print(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint 2: 10km Emergency SOS Radius Dispatcher
@app.post("/api/v1/sos/trigger")
def trigger_sos(payload: SOSPayload, db: Session = Depends(get_db)):
    """
    Finds all doctors within 10km (10,000 meters) using PostGIS ST_DWithin
    """
    sos_query = text("""
        SELECT id::text, full_name, mobile_number, fcm_token
        FROM doctor_profiles
        WHERE ST_DWithin(
            location,
            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
            10000
        )
        AND id::text != :sender_id;
    """)

    try:
        nearby_doctors = db.execute(
            sos_query,
            {"lng": payload.longitude, "lat": payload.latitude, "sender_id": payload.doctor_id}
        ).fetchall()

        alerted_list = [{"name": doc.full_name, "mobile": doc.mobile_number} for doc in nearby_doctors]

        return {
            "status": "SOS_BROADCAST_SUCCESS",
            "alerted_count": len(alerted_list),
            "alerted_doctors": alerted_list,
            "message": f"Alert dispatched to {len(alerted_list)} doctor(s) within 10km radius."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))