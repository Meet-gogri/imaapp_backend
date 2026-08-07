import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DoctorModel, OtpCodeModel
from ..schemas import SendOtpRequest, VerifyOtpRequest
from ..security import generate_otp_code, hash_code, create_access_token, OTP_EXPIRES_MINUTES, OTP_MAX_ATTEMPTS
from ..utils.mailer import send_otp_email, send_otp_sms

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/send-otp")
async def send_otp(data: SendOtpRequest, db: Session = Depends(get_db)):
    identifier = data.identifier.strip()
    purpose = data.purpose.strip().lower()
    is_email = "@" in identifier

    user = db.query(DoctorModel).filter(
        (DoctorModel.mobile_number == identifier) | (DoctorModel.email == identifier)
    ).first()
    user_exists = user is not None

    if purpose == "signin" and not user_exists:
        raise HTTPException(status_code=400, detail="This mobile number or email is not registered. Please register first.")
    if purpose == "signup" and user_exists:
        raise HTTPException(status_code=400, detail="Account already exists. Please sign in instead.")

    code = generate_otp_code()
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=OTP_EXPIRES_MINUTES)

    otp_row = OtpCodeModel(
        identifier=identifier,
        purpose=purpose,
        code_hash=hash_code(code, identifier),
        expires_at=expires_at,
    )
    db.add(otp_row)
    db.commit()

    if is_email:
        send_otp_email(identifier, code)
    else:
        send_otp_sms(identifier, code)

    return {"status": "success", "message": f"OTP sent to {identifier}", "expiresInSeconds": OTP_EXPIRES_MINUTES * 60}


@router.post("/verify-otp")
async def verify_otp(data: VerifyOtpRequest, db: Session = Depends(get_db)):
    identifier = data.identifier.strip()
    purpose = data.purpose.strip().lower()
    code = data.code.strip()

    otp_row = (
        db.query(OtpCodeModel)
        .filter(
            OtpCodeModel.identifier == identifier,
            OtpCodeModel.purpose == purpose,
            OtpCodeModel.consumed == False,  # noqa: E712
        )
        .order_by(OtpCodeModel.created_at.desc())
        .first()
    )

    if otp_row is None:
        raise HTTPException(status_code=401, detail="No pending code for this identifier - request a new OTP")

    if otp_row.expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=401, detail="Code expired - request a new OTP")

    if otp_row.attempts >= OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=401, detail="Too many incorrect attempts - request a new OTP")

    if otp_row.code_hash != hash_code(code, identifier):
        otp_row.attempts += 1
        db.commit()
        raise HTTPException(status_code=401, detail="Incorrect code")

    # Correct code - consume it so it can't be replayed
    otp_row.consumed = True
    db.commit()

    is_email = "@" in identifier
    doctor = db.query(DoctorModel).filter(
        (DoctorModel.mobile_number == identifier) | (DoctorModel.email == identifier)
    ).first()

    is_new_user = False
    if doctor is None:
        doctor = DoctorModel(
            email=identifier if is_email else None,
            mobile_number=identifier if not is_email else None,
            profile_complete=False,
        )
        db.add(doctor)
        db.commit()
        db.refresh(doctor)
        is_new_user = True

    token = create_access_token(doctor.id)

    return {
        "status": "success",
        "token": token,
        "isNewUser": is_new_user or not doctor.profile_complete,
        "doctor": {
            "id": doctor.id,
            "full_name": doctor.full_name,
            "mobile_number": doctor.mobile_number,
            "email": doctor.email,
            "qualification": doctor.qualification,
            "address": doctor.address,
            "pincode": doctor.pincode,
            "city": doctor.city,
            "state": doctor.state,
        },
    }
