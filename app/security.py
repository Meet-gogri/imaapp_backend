import os
import hashlib
import secrets
import datetime
import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-change-this-before-any-real-demo")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_DAYS = 30

OTP_EXPIRES_MINUTES = 5
OTP_MAX_ATTEMPTS = 5  # after this many wrong tries, the code is dead even if not expired


def generate_otp_code() -> str:
    # 6 digits, cryptographically random (not just `random.randint`)
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_code(code: str, identifier: str) -> str:
    # Salting with the identifier means two users who happen to get the same
    # code don't produce the same hash. Codes are never stored in plain text.
    return hashlib.sha256(f"{identifier}:{code}".encode()).hexdigest()


def create_access_token(doctor_id: int) -> str:
    payload = {
        "doctor_id": doctor_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=JWT_EXPIRES_DAYS),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    """Returns doctor_id if valid, raises jwt exceptions otherwise."""
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    return payload["doctor_id"]
