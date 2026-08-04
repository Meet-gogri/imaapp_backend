from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os

# ==========================================
# 1. DATABASE CONFIGURATION (SQLAlchemy)
# ==========================================
# Update your DATABASE_URL if you are using PostgreSQL or SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./policyera_ima.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Model for Doctor Profiles
class DoctorModel(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    mobile_number = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String, nullable=False)
    qualification = Column(String, nullable=False)
    address = Column(String, nullable=False)
    pincode = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    ima_branch_name = Column(String, default="General")
    ima_membership_no = Column(String, default="N/A")

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 2. FASTAPI APP & CORS SETUP
# ==========================================
app = FastAPI(
    title="PolicyEra IMA Portal Backend",
    version="1.0.0"
)

# Enable CORS so your Flutter Web/App can talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 3. PYDANTIC SCHEMAS
# ==========================================
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

# (Assuming your app, database session, and DoctorModel are already initialized above)

class AuthRequest(BaseModel):
    identifier: str
    purpose: str

@app.post("/api/v1/auth/send-otp")
async def send_otp(data: AuthRequest, db: Session = Depends(get_db)):
    identifier = data.identifier.strip()
    purpose = data.purpose.strip().lower()

    # Query database to check if user already exists
    user = db.query(DoctorModel).filter(
        (DoctorModel.mobile_number == identifier) | (DoctorModel.email == identifier)
    ).first()
    
    user_exists = user is not None

    if purpose == "signin" and not user_exists:
        raise HTTPException(
            status_code=400,
            detail="This mobile number or email is not registered. Please register first."
        )

    if purpose == "signup" and user_exists:
        raise HTTPException(
            status_code=400,
            detail="Account already exists. Please sign in instead."
        )

    # Base response
    response_data = {
        "status": "success",
        "message": f"OTP sent successfully to {identifier}",
        "purpose": purpose
    }
    
    # Attach doctor profile if it's a sign-in so Flutter can display their actual data
    if purpose == "signin" and user:
        response_data["doctor"] = {
            "full_name": user.full_name,
            "mobile_number": user.mobile_number,
            "email": user.email,
            "pincode": user.pincode,
            "city": user.city,
            "state": user.state
        }

    return response_data

class DoctorProfileSchema(BaseModel):
    mobile_number: str | None = None
    email: str | None = None
    full_name: str
    qualification: str
    address: str
    pincode: str
    city: str
    state: str
    ima_branch_name: str | None = "General"
    ima_membership_no: str | None = "N/A"

class SOSRequest(BaseModel):
    city: str
    state: str
    pincode: str

# ==========================================
# 4. API ENDPOINTS
# ==========================================

@app.get("/")
def read_root():
    return {"message": "Welcome to PolicyEra IMA Portal Backend API"}

@app.post("/api/v1/auth/send-otp")
async def send_otp(data: AuthRequest, db: Session = Depends(get_db)):
    identifier = data.identifier.strip()
    purpose = data.purpose.strip().lower()

@app.get("/api/doctors/list")
def get_registered_doctors():
    # Query your database to fetch all registered doctor profiles
    # and return them as a JSON list.
    return {"doctors": all_registered_doctors_from_db}    

    # Query database to check if user already exists
    user_exists = db.query(DoctorModel).filter(
        (DoctorModel.mobile_number == identifier) | (DoctorModel.email == identifier)
    ).first() is not None

    # Strict Rule 1: Block Sign In if the user is NOT registered in the database
    if purpose == "signin" and not user_exists:
        raise HTTPException(
            status_code=400,
            detail="This mobile number or email is not registered. Please register first."
        )

    # Strict Rule 2: Block Registration if the account ALREADY exists
    if purpose == "signup" and user_exists:
        raise HTTPException(
            status_code=400,
            detail="Account already exists. Please sign in instead."
        )

    # In production, integrate your SMS/Email OTP provider here (e.g., Twilio, Fast2SMS)
    # For testing, we mock successful OTP generation/dispatch:
    return {
        "status": "success",
        "message": f"OTP sent successfully to {identifier}",
        "purpose": purpose
    }

@app.post("/api/doctors/profile", status_code=201)
async def create_or_update_doctor_profile(profile: DoctorProfileSchema, db: Session = Depends(get_db)):
    # Check if doctor profile already exists via mobile or email
    existing_doctor = None
    if profile.mobile_number:
        existing_doctor = db.query(DoctorModel).filter(DoctorModel.mobile_number == profile.mobile_number).first()
    elif profile.email:
        existing_doctor = db.query(DoctorModel).filter(DoctorModel.email == profile.email).first()

    if existing_doctor:
        # Update existing record
        existing_doctor.full_name = profile.full_name
        existing_doctor.qualification = profile.qualification
        existing_doctor.address = profile.address
        existing_doctor.pincode = profile.pincode
        existing_doctor.city = profile.city
        existing_doctor.state = profile.state
        existing_doctor.ima_branch_name = profile.ima_branch_name or existing_doctor.ima_branch_name
        existing_doctor.ima_membership_no = profile.ima_membership_no or existing_doctor.ima_membership_no
    else:
        # Create new profile entry
        new_doctor = DoctorModel(
            mobile_number=profile.mobile_number,
            email=profile.email,
            full_name=profile.full_name,
            qualification=profile.qualification,
            address=profile.address,
            pincode=profile.pincode,
            city=profile.city,
            state=profile.state,
            ima_branch_name=profile.ima_branch_name or "General",
            ima_membership_no=profile.ima_membership_no or "N/A"
        )
        db.add(new_doctor)
    
    db.commit()
    return {"status": "success", "message": "Doctor profile saved successfully"}

@app.post("/api/v1/sos/broadcast")
async def trigger_sos_broadcast(sos: SOSRequest):
    # Logic to alert nearby doctors within 10km radius based on pincode/city
    return {
        "status": "broadcasted",
        "message": f"Emergency broadcast successfully dispatched to doctors near {sos.city}, {sos.state} ({sos.pincode})"
    }