from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DoctorModel
from ..schemas import DoctorProfileUpdate
from ..deps import get_current_doctor
from ..utils.geo import geocode_pincode

router = APIRouter(prefix="/api/doctors", tags=["profile"])


def _serialize(doctor: DoctorModel):
    return {
        "id": doctor.id,
        "full_name": doctor.full_name,
        "mobile_number": doctor.mobile_number,
        "email": doctor.email,
        "qualification": doctor.qualification,
        "address": doctor.address,
        "pincode": doctor.pincode,
        "city": doctor.city,
        "state": doctor.state,
        "ima_branch_name": doctor.ima_branch_name,
        "ima_membership_no": doctor.ima_membership_no,
        "profile_complete": doctor.profile_complete,
        "has_location": doctor.latitude is not None and doctor.longitude is not None,
    }


@router.get("/me")
def get_my_profile(current: DoctorModel = Depends(get_current_doctor)):
    return _serialize(current)


@router.put("/me", status_code=200)
def update_my_profile(
    profile: DoctorProfileUpdate,
    db: Session = Depends(get_db),
    current: DoctorModel = Depends(get_current_doctor),
):
    current.full_name = profile.full_name
    current.qualification = profile.qualification
    current.address = profile.address
    current.pincode = profile.pincode
    current.city = profile.city
    current.state = profile.state
    current.ima_branch_name = profile.ima_branch_name or current.ima_branch_name
    current.ima_membership_no = profile.ima_membership_no or current.ima_membership_no
    current.profile_complete = True

    # Resolve pincode -> coordinates once here, cached for every future SOS
    # radius search. If it fails (bad pincode, geocoder briefly down), the
    # profile still saves - it just won't be reachable by SOS yet.
    coords = geocode_pincode(profile.pincode)
    if coords:
        current.latitude, current.longitude = coords

    db.commit()
    db.refresh(current)

    return {"status": "success", "message": "Profile saved successfully", "doctor": _serialize(current)}


@router.get("/list")
def list_registered_doctors(
    db: Session = Depends(get_db),
    current: DoctorModel = Depends(get_current_doctor),  # directory is member-only, not public
):
    doctors = db.query(DoctorModel).filter(DoctorModel.profile_complete == True).all()  # noqa: E712
    return {
        "doctors": [
            {
                "id": d.id,
                "full_name": d.full_name,
                "qualification": d.qualification,
                "address": d.address,
                "pincode": d.pincode,
                "city": d.city,
                "state": d.state,
            }
            for d in doctors
        ]
    }
