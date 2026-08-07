from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DoctorModel, SosAlertModel, SosRecipientModel
from ..schemas import SosTriggerRequest, SosResolveRequest
from ..deps import get_current_doctor
from ..utils.geo import haversine_km

router = APIRouter(prefix="/api/v1/sos", tags=["sos"])

DEFAULT_RADIUS_KM = 10


@router.post("/trigger", status_code=201)
def trigger_sos(
    payload: SosTriggerRequest,
    db: Session = Depends(get_db),
    current: DoctorModel = Depends(get_current_doctor),
):
    if current.latitude is None or current.longitude is None:
        raise HTTPException(
            status_code=400,
            detail="Your profile has no confirmed location yet. Save your profile with a valid pincode before using SOS.",
        )

    radius = payload.radius_km or DEFAULT_RADIUS_KM

    alert = SosAlertModel(
        sender_id=current.id,
        latitude=current.latitude,
        longitude=current.longitude,
        pincode=current.pincode,
        radius_km=radius,
        note=payload.note,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    # Plain-Python radius search - see app/utils/geo.py. Fine at the scale of
    # a single state association; if the doctor table grows very large later,
    # this is the spot to swap in a spatial index (e.g. Postgres + PostGIS).
    candidates = db.query(DoctorModel).filter(
        DoctorModel.id != current.id,
        DoctorModel.latitude.isnot(None),
        DoctorModel.longitude.isnot(None),
    ).all()

    notified = []
    for doc in candidates:
        distance = haversine_km(current.latitude, current.longitude, doc.latitude, doc.longitude)
        if distance <= radius:
            db.add(SosRecipientModel(alert_id=alert.id, doctor_id=doc.id, distance_km=round(distance, 2)))
            notified.append({"id": doc.id, "full_name": doc.full_name, "distance_km": round(distance, 2)})

    db.commit()
    notified.sort(key=lambda d: d["distance_km"])

    return {
        "alert_id": alert.id,
        "created_at": alert.created_at,
        "radius_km": radius,
        "doctors_notified": len(notified),
        "notified_doctors": notified,
    }


@router.get("/my-alerts")
def my_alerts(
    db: Session = Depends(get_db),
    current: DoctorModel = Depends(get_current_doctor),
):
    # Simple polling endpoint for the "My Alerts" screen. Real push
    # notifications (so recipients are pinged even with the app closed) need
    # a free Firebase Cloud Messaging project wired in as a next step - this
    # endpoint works today without that setup.
    sent = db.query(SosAlertModel).filter(SosAlertModel.sender_id == current.id).order_by(SosAlertModel.created_at.desc()).all()

    received_rows = (
        db.query(SosRecipientModel, SosAlertModel, DoctorModel)
        .join(SosAlertModel, SosRecipientModel.alert_id == SosAlertModel.id)
        .join(DoctorModel, SosAlertModel.sender_id == DoctorModel.id)
        .filter(SosRecipientModel.doctor_id == current.id)
        .order_by(SosAlertModel.created_at.desc())
        .all()
    )

    return {
        "sent": [
            {
                "alert_id": a.id, "status": a.status, "note": a.note,
                "radius_km": a.radius_km, "created_at": a.created_at, "resolved_at": a.resolved_at,
            }
            for a in sent
        ],
        "received": [
            {
                "alert_id": alert.id,
                "sender_name": sender.full_name,
                "distance_km": recipient.distance_km,
                "status": alert.status,
                "created_at": alert.created_at,
                "acknowledged": recipient.acknowledged_at is not None,
            }
            for recipient, alert, sender in received_rows
        ],
    }


@router.post("/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    payload: SosResolveRequest,
    db: Session = Depends(get_db),
    current: DoctorModel = Depends(get_current_doctor),
):
    if payload.status not in ("resolved", "false_alarm"):
        raise HTTPException(status_code=400, detail="status must be 'resolved' or 'false_alarm'")

    alert = db.query(SosAlertModel).filter(SosAlertModel.id == alert_id, SosAlertModel.sender_id == current.id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    import datetime
    alert.status = payload.status
    alert.resolved_at = datetime.datetime.utcnow()
    db.commit()
    return {"status": "success", "alert_status": alert.status}


@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current: DoctorModel = Depends(get_current_doctor),
):
    recipient = db.query(SosRecipientModel).filter(
        SosRecipientModel.alert_id == alert_id, SosRecipientModel.doctor_id == current.id
    ).first()
    if recipient is None:
        raise HTTPException(status_code=404, detail="You were not notified for this alert")

    import datetime
    recipient.acknowledged_at = datetime.datetime.utcnow()
    db.commit()
    return {"status": "success"}
