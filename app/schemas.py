from pydantic import BaseModel


class SendOtpRequest(BaseModel):
    identifier: str
    purpose: str  # "signin" | "signup"


class VerifyOtpRequest(BaseModel):
    identifier: str
    code: str
    purpose: str


class DoctorProfileUpdate(BaseModel):
    full_name: str
    qualification: str
    address: str
    pincode: str
    city: str
    state: str
    ima_branch_name: str | None = "General"
    ima_membership_no: str | None = "N/A"


class SosTriggerRequest(BaseModel):
    note: str | None = None
    radius_km: float | None = None


class SosResolveRequest(BaseModel):
    status: str  # "resolved" | "false_alarm"
