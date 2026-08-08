import datetime
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# TEMPORARY DEBUG SWITCH - off unless explicitly turned on via Render's
# Environment tab. When on, the code "123456" is accepted for ANY account,
# skipping real verification entirely. This exists only to unblock testing
# while you're debugging deploys. Set DEV_BYPASS_OTP=true on Render to turn
# it on, and DELETE that environment variable again before anyone outside
# your own testing touches the app - this is the exact hole we fixed earlier.
DEV_BYPASS_OTP = os.getenv("DEV_BYPASS_OTP", "false").lower() == "true"
DEV_BYPASS_CODE = "123456"

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
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=OTP_EXPIRES_MINUTES)

    otp_row = OtpCodeModel(
        identifier=identifier,
        purpose=purpose,
        code_hash=hash_code(code, identifier),
        expires_at=expires_at,
    )
    db.add(otp_row)
    db.commit()

    try:
        if is_email:
            send_otp_email(identifier, code)
        else:
            send_otp_sms(identifier, code)
    except Exception as exc:
        # An SMTP misconfiguration (wrong password, wrong host, etc.) should
        # not take down the whole request - log the real reason clearly and
        # tell the caller plainly instead of a raw 500 crash.
        print(f"[OTP EMAIL/SMS SEND FAILED] identifier={identifier} error={exc}")
        raise HTTPException(
            status_code=500,
            detail="Could not send the verification code right now. Check backend SMTP settings.",
        )

    return {"status": "success", "message": f"OTP sent to {identifier}", "expiresInSeconds": OTP_EXPIRES_MINUTES * 60}


@router.post("/verify-otp")
async def verify_otp(data: VerifyOtpRequest, db: Session = Depends(get_db)):
    identifier = data.identifier.strip()
    purpose = data.purpose.strip().lower()
    code = data.code.strip()

    if DEV_BYPASS_OTP and code == DEV_BYPASS_CODE:
        # Debug path only - real OTP row is neither checked nor required.
        pass
    else:
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

        if otp_row.expires_at < datetime.datetime.now(datetime.timezone.utc):
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