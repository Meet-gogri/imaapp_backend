import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ==========================================
# 1. DATABASE CONFIGURATION (SQLAlchemy)
# ==========================================
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
class AuthRequest(BaseModel):
    identifier: str
    purpose: str

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

class DoctorUpdateSchema(BaseModel):
    full_name: str | None = None
    qualification: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    ima_branch_name: str | None = None
    ima_membership_no: str | None = None

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

    response_data = {
        "status": "success",
        "message": f"OTP sent successfully to {identifier}",
        "purpose": purpose
    }
    
    # Attach doctor profile on sign-in so Flutter can display their actual data
    if purpose == "signin" and user:
        response_data["doctor"] = {
            "id": user.id,
            "full_name": user.full_name,
            "mobile_number": user.mobile_number,
            "email": user.email,
            "qualification": user.qualification,
            "address": user.address,
            "pincode": user.pincode,
            "city": user.city,
            "state": user.state,
            "ima_branch_name": user.ima_branch_name,
            "ima_membership_no": user.ima_membership_no
        }

    return response_data

@app.post("/api/doctors/profile", status_code=201)
async def create_or_update_doctor_profile(profile: DoctorProfileSchema, db: Session = Depends(get_db)):
    existing_doctor = None
    if profile.mobile_number:
        existing_doctor = db.query(DoctorModel).filter(DoctorModel.mobile_number == profile.mobile_number).first()
    elif profile.email:
        existing_doctor = db.query(DoctorModel).filter(DoctorModel.email == profile.email).first()

    if existing_doctor:
        existing_doctor.full_name = profile.full_name
        existing_doctor.qualification = profile.qualification
        existing_doctor.address = profile.address
        existing_doctor.pincode = profile.pincode
        existing_doctor.city = profile.city
        existing_doctor.state = profile.state
        existing_doctor.ima_branch_name = profile.ima_branch_name or existing_doctor.ima_branch_name
        existing_doctor.ima_membership_no = profile.ima_membership_no or existing_doctor.ima_membership_no
    else:
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

@app.get("/api/doctors/list")
def get_registered_doctors(db: Session = Depends(get_db)):
    # Safely query database for all registered doctors
    doctors = db.query(DoctorModel).all()
    return {
        "doctors": [
            {
                "id": doc.id,
                "full_name": doc.full_name,
                "mobile_number": doc.mobile_number,
                "email": doc.email,
                "qualification": doc.qualification,
                "address": doc.address,
                "pincode": doc.pincode,
                "city": doc.city,
                "state": doc.state,
                "ima_branch_name": doc.ima_branch_name,
                "ima_membership_no": doc.ima_membership_no
            } for doc in doctors
        ]
    }

@app.put("/api/doctors/update/{doctor_id}")
def update_doctor_profile(doctor_id: int, update_data: DoctorUpdateSchema, db: Session = Depends(get_db)):
    doctor = db.query(DoctorModel).filter(DoctorModel.id == doctor_id).first()
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    if update_data.full_name is not None:
        doctor.full_name = update_data.full_name
    if update_data.qualification is not None:
        doctor.qualification = update_data.qualification
    if update_data.address is not None:
        doctor.address = update_data.address
    if update_data.city is not None:
        doctor.city = update_data.city
    if update_data.state is not None:
        doctor.state = update_data.state
    if update_data.pincode is not None:
        doctor.pincode = update_data.pincode
    if update_data.ima_branch_name is not None:
        doctor.ima_branch_name = update_data.ima_branch_name
    if update_data.ima_membership_no is not None:
        doctor.ima_membership_no = update_data.ima_membership_no
        
    db.commit()
    db.refresh(doctor)
    
    return {
        "status": "success",
        "message": "Profile updated successfully",
        "doctor": {
            "id": doctor.id,
            "full_name": doctor.full_name,
            "qualification": doctor.qualification,
            "address": doctor.address,
            "city": doctor.city,
            "state": doctor.state,
            "pincode": doctor.pincode
        }
    }

@app.post("/api/v1/sos/broadcast")
async def trigger_sos_broadcast(sos: SOSRequest):
    return {
        "status": "broadcasted",
        "message": f"Emergency broadcast successfully dispatched to doctors near {sos.city}, {sos.state} ({sos.pincode})"
    }

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# Pydantic model for incoming update fields
class DoctorUpdate(BaseModel):
    full_name: Optional[str] = None
    qualification: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

@app.put("/api/doctors/{doctor_id}")
async def update_doctor_profile(doctor_id: str, payload: DoctorUpdate):
    # Filter out null values so only provided fields get updated
    update_data = {k: v for k, v in payload.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")
    
    # TODO: Replace with your actual database update logic (e.g., MongoDB or SQLAlchemy)
    # Example:
    # result = await db.doctors.update_one({"_id": doctor_id}, {"$set": update_data})
    # if result.matched_count == 0:
    #     raise HTTPException(status_code=404, detail="Doctor not found")

    return {
        "status": "success",
        "message": "Doctor profile updated successfully",
        "updated_fields": update_data
    }


    import 'package:url_launcher/url_launcher.dart';

Future<void> _launchExternalBrowser(String urlString) async {
  final Uri url = Uri.parse(urlString);
  if (!await launchUrl(
    url,
    mode: LaunchMode.externalApplication, // Forces it to open in Chrome / default browser
  )) {
    throw Exception('Could not launch $urlString');
  }
}