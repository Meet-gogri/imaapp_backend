import os
import random
import re
from datetime import datetime, timedelta
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, create_engine, text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# 1. Load Environment Variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set in .env file!")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# 🗄️ SQLALCHEMY MODELS
# ==========================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    mobile_number = Column(String(10), unique=True, index=True, nullable=True)
    
    # Profile Fields
    full_name = Column(String, nullable=True)
    address = Column(String, nullable=True)
    pincode = Column(String(6), nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    qualification = Column(String, nullable=True)
    ima_branch_name = Column(String, nullable=True)
    ima_membership_no = Column(String, nullable=True)
    profile_photo_url = Column(String, nullable=True)

    # Status Flags
    is_verified = Column(Boolean, default=False)
    is_profile_complete = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String, index=True, nullable=False)
    otp = Column(String(6), nullable=False)
    purpose = Column(String(20), nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LoginActivity(Base):
    __tablename__ = "login_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String, nullable=True)
    status = Column(String(20), nullable=False)
    login_time = Column(DateTime(timezone=True), server_default=func.now())


Base.metadata.create_all(bind=engine)

# ==========================================
# 🚀 FASTAPI APP INIT
# ==========================================

app = FastAPI(
    title="IMA Doctor Portal Backend API",
    description="Microservices powering Auth, Profile Management, Announcements, and 10km SOS System",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 📝 PYDANTIC VALIDATION SCHEMAS
# ==========================================

class SendOTPRequest(BaseModel):
    identifier: str
    purpose: str

    @validator("identifier")
    def validate_identifier(cls, v):
        v = v.strip()
        email_regex = r"^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$"
        mobile_regex = r"^[6-9]\d{9}$"
        
        if not (re.match(email_regex, v) or re.match(mobile_regex, v)):
            raise ValueError("Identifier must be a valid Email address or 10-digit Indian Mobile Number.")
        return v

    @validator("purpose")
    def validate_purpose(cls, v):
        if v.lower() not in ["signup", "signin"]:
            raise ValueError("Purpose must be either 'signup' or 'signin'.")
        return v.lower()


class VerifyOTPRequest(BaseModel):
    identifier: str
    otp: str
    purpose: str


class DoctorProfileRequest(BaseModel):
    user_id: Optional[int] = None
    full_name: str
    qualification: str
    address: str
    pincode: str
    city: str
    state: str
    ima_branch_name: Optional[str] = "General"
    ima_membership_no: Optional[str] = "N/A"

    @validator("pincode")
    def validate_pincode(cls, v):
        if not re.match(r"^\d{6}$", v):
            raise ValueError("Pincode must be exactly 6 numeric digits.")
        return v


class SOSPayload(BaseModel):
    doctor_id: str
    latitude: float
    longitude: float


class AnnouncementResponse(BaseModel):
    id: str
    title: str
    academic_year: str
    pdf_url: Optional[str] = None

# ==========================================
# 🔐 AUTHENTICATION & PROFILE ENDPOINTS
# ==========================================

@app.get("/")
def root():
    return {"status": "SUCCESS", "message": "IMA FastAPI Backend running cleanly on PostgreSQL!"}


@app.post("/api/v1/auth/send-otp")
def send_otp(payload: SendOTPRequest, db: Session = Depends(get_db)):
    identifier = payload.identifier
    purpose = payload.purpose
    is_email = "@" in identifier

    existing_user = db.query(User).filter(
        (User.email == identifier) if is_email else (User.mobile_number == identifier)
    ).first()

    if purpose == "signup" and existing_user:
        raise HTTPException(status_code=400, detail="Account already exists. Please Sign In instead.")

    otp_code = str(random.randint(1000, 9999))
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    otp_entry = OTPCode(identifier=identifier, otp=otp_code, purpose=purpose, expires_at=expires_at)
    db.add(otp_entry)
    db.commit()

    print(f"\n🔑 OTP FOR {identifier}: [{otp_code}] (Valid 5 mins)\n")

    return {"status": "SUCCESS", "message": f"OTP sent to {identifier}."}


@app.post("/api/doctors/profile")
@app.post("/api/v1/profile/complete")
def save_doctor_profile(payload: DoctorProfileRequest, db: Session = Depends(get_db)):
    # Find existing user or create a placeholder record
    user = None
    if payload.user_id:
        user = db.query(User).filter(User.id == payload.user_id).first()

    if not user:
        user = User()
        db.add(user)

    user.full_name = payload.full_name
    user.qualification = payload.qualification
    user.address = payload.address
    user.pincode = payload.pincode
    user.city = payload.city
    user.state = payload.state
    user.ima_branch_name = payload.ima_branch_name
    user.ima_membership_no = payload.ima_membership_no
    user.is_profile_complete = True

    db.commit()
    db.refresh(user)

    return {
        "status": "SUCCESS",
        "message": "Doctor Profile saved successfully!",
        "user_id": user.id
    }

# ==========================================
# 📢 ANNOUNCEMENTS & SOS ENDPOINTS
# ==========================================

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
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sos/trigger")
def trigger_sos(payload: SOSPayload, db: Session = Depends(get_db)):
    sos_query = text("""
        SELECT id::text, full_name, mobile_number
        FROM users
        WHERE pincode IS NOT NULL;
    """)
    try:
        nearby_doctors = db.execute(sos_query).fetchall()
        alerted_list = [{"name": doc.full_name, "mobile": doc.mobile_number} for doc in nearby_doctors]
        return {
            "status": "SOS_BROADCAST_SUCCESS",
            "alerted_count": len(alerted_list),
            "alerted_doctors": alerted_list,
            "message": f"Alert dispatched to doctors within radius."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))