from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.sql import func
from .database import Base


class DoctorModel(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    mobile_number = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String, nullable=True)
    qualification = Column(String, nullable=True)
    address = Column(String, nullable=True)
    pincode = Column(String, nullable=True, index=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    ima_branch_name = Column(String, default="General")
    ima_membership_no = Column(String, default="N/A")

    # Resolved once when a pincode is saved (see app/utils/geo.py) and then
    # reused for every SOS radius search - no live geocoding call per alert.
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    profile_complete = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Profile photo stored as base64 text directly in the database - avoids
    # needing any paid file/object storage service. Keep photos small on the
    # Flutter side (resize before upload) since this bloats each DB row.
    photo_base64 = Column(Text, nullable=True)


class OtpCodeModel(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String, index=True, nullable=False)  # email or mobile
    purpose = Column(String, nullable=False)  # 'signin' or 'signup'
    code_hash = Column(String, nullable=False)  # never store the plain code
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)  # guards against brute-forcing the code
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SosAlertModel(Base):
    __tablename__ = "sos_alerts"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    pincode = Column(String, nullable=True)
    radius_km = Column(Float, default=10)
    status = Column(String, default="active")  # active | resolved | false_alarm
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class SosRecipientModel(Base):
    __tablename__ = "sos_recipients"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("sos_alerts.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    distance_km = Column(Float, nullable=True)
    notified_at = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)