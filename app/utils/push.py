import os
import firebase_admin
from firebase_admin import credentials, messaging

_firebase_app = None


def _get_firebase_app():
    """Lazily initializes the Firebase Admin SDK using a credentials file
    path from FIREBASE_CREDENTIALS_PATH. On Render, this points at a Secret
    File (e.g. /etc/secrets/firebase-service-account.json) - the actual key
    contents are never committed to GitHub or hardcoded here."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if not cred_path or not os.path.exists(cred_path):
        print(f"[push] FIREBASE_CREDENTIALS_PATH not set or file missing ({cred_path}) - push notifications disabled")
        return None

    try:
        cred = credentials.Certificate(cred_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        print("[push] Firebase Admin initialized")
        return _firebase_app
    except Exception as exc:
        print(f"[push] Failed to initialize Firebase Admin: {exc}")
        return None


def send_push_notification(token: str, title: str, body: str, data: dict | None = None):
    """Sends a real push notification to one device token. Safe to call even
    if Firebase isn't configured yet - just logs and does nothing."""
    app = _get_firebase_app()
    if app is None or not token:
        return False

    try:
        message = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            android=messaging.AndroidConfig(priority="high"),
        )
        messaging.send(message, app=app)
        return True
    except Exception as exc:
        print(f"[push] Failed to send to token={token[:12]}...: {exc}")
        return False