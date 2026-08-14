from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DoctorModel
from ..schemas import RegisterPushTokenRequest
from ..deps import get_current_doctor

router = APIRouter(prefix="/api/v1/push", tags=["push"])


@router.post("/register-token")
def register_token(
    payload: RegisterPushTokenRequest,
    db: Session = Depends(get_db),
    current: DoctorModel = Depends(get_current_doctor),
):
    current.fcm_token = payload.fcm_token
    db.commit()
    return {"status": "success"}