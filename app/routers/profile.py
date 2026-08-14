from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DoctorModel
from ..schemas import DoctorProfileUpdate
from ..deps import get_current_doctor
from ..utils.geo import geocode_pincode, geocode_city_state, geocode_from_city_lookup

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
        "photo_base64": doctor.photo_base64,
        "has_location": doctor.latitude is not None and doctor.longitude is not None,
    }


def _with_dr_prefix(name: str) -> str:
    if not name:
        return name
    stripped = name.strip()
    lowered = stripped.lower()
    if lowered.startswith("dr.") or lowered.startswith("dr "):
        return stripped
    return f"Dr. {stripped}"


@router.get("/me")
def get_my_profile(current: DoctorModel = Depends(get_current_doctor)):
    return _serialize(current)


@router.put("/me", status_code=200)
def update_my_profile(
    profile: DoctorProfileUpdate,
    db: Session = Depends(get_db),
    current: DoctorModel = Depends(get_current_doctor),
):
    current.full_name = _with_dr_prefix(profile.full_name)
    current.qualification = profile.qualification
    current.address = profile.address
    current.pincode = profile.pincode
    current.city = profile.city
    current.state = profile.state
    current.ima_branch_name = profile.ima_branch_name or current.ima_branch_name
    current.ima_membership_no = profile.ima_membership_no or current.ima_membership_no
    current.profile_complete = True
    if profile.photo_base64 is not None:
        current.photo_base64 = profile.photo_base64

    # Resolve pincode -> coordinates once here, cached for every future SOS
    # radius search. Built-in Maharashtra city lookup first - it's the
    # reliable path since it needs no network call at all. Nominatim is kept
    # as a secondary best-effort attempt only, since Render's IP range is
    # currently blocked by their free service (see app/utils/geo.py notes).
    coords = geocode_from_city_lookup(profile.city, profile.state)
    if not coords:
        coords = geocode_pincode(profile.pincode)
    if not coords:
        coords = geocode_city_state(profile.city, profile.state)
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
                "photo_base64": d.photo_base64,
            }
            for d in doctors
        ]
    }