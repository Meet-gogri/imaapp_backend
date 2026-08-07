from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/insurance", tags=["insurance"])

# Flip "available" to True and fill in the real fields once PolicyEra shares
# the integration API - the Flutter app reads this endpoint, so that's a
# backend-only change, no app store update required.
@router.get("/status")
def insurance_status():
    return {
        "available": False,
        "title": "Indemnity Policy Purchase - Coming Soon",
        "message": "In-app policy purchase is being integrated with PolicyEra. "
                   "Meanwhile you can visit the PolicyEra website directly.",
        "external_url": "https://policyera.com",
    }
