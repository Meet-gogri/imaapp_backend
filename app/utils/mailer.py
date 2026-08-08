import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_FROM = os.getenv("SMTP_FROM")


def send_otp_email(to_email: str, code: str):
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        # Dev/demo mode: no SMTP configured yet, so just log it. This is what
        # lets you test the whole flow before setting up a free Gmail account.
        print(f"[DEV MODE - no SMTP configured] OTP for {to_email}: {code}")
        return

    msg = EmailMessage()
    msg["Subject"] = "Your IMA Maharashtra App verification code"
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(f"Your verification code is {code}. It expires in 5 minutes.")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


def send_otp_sms(to_mobile: str, code: str):
    # No free SMS gateway exists for India - every provider (Twilio, MSG91,
    # etc.) is paid per-message. Until you choose and pay for one, mobile
    # sign-up falls back to this console log so you can still test locally.
    # Wire your chosen provider's API call in here when you're ready - the
    # rest of the auth flow (hashing, expiry, verification) doesn't change.
    print(f"[DEV MODE - no SMS gateway configured] OTP for {to_mobile}: {code}")
