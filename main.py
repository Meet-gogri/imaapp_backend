import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# Database configuration (Uses environment variable for production/Render or falls back to local SQLite)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./doctors.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Model for Doctors
class DoctorModel(Base):
    __tablename__ = "doctors"
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    qualification = Column(String)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    pincode = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="IMA App Backend", version="1.0.0")

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Schema for Updates
class DoctorUpdateSchema(BaseModel):
    full_name: str | None = None
    qualification: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None

@app.get("/")
def read_root():
    return {"status": "Running", "message": "IMA Backend API is active"}

@app.get("/api/doctors/list")
def get_registered_doctors(db: Session = Depends(get_db)):
    doctors = db.query(DoctorModel).all()
    return {
        "doctors": [
            {
                "id": doc.id,
                "full_name": doc.full_name,
                "qualification": doc.qualification,
                "address": doc.address,
                "city": doc.city,
                "state": doc.state,
                "pincode": doc.pincode
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
        
    db.commit()
    db.refresh(doctor)
    
    return {
        "message": "Profile updated successfully",
        "doctor": {
            "id": doctor.id,
            "full_name": doc.full_name,
            "qualification": doc.qualification,
            "address": doc.address,
            "city": doc.city,
            "state": doc.state,
            "pincode": doc.pincode
        }
    }