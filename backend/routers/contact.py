import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter
from pydantic import BaseModel

from config import settings

router = APIRouter()


class ContactRequest(BaseModel):
    name: str
    email: str
    message: str


@router.post("/contact")
def contact(req: ContactRequest) -> dict:
    if settings.smtp_host and settings.smtp_user:
        try:
            msg = MIMEMultipart()
            msg["From"] = settings.smtp_user
            msg["To"] = settings.smtp_user
            msg["Subject"] = f"Bloxp contact from {req.name}"
            body = f"From: {req.name} <{req.email}>\n\n{req.message}"
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_pass)
                server.send_message(msg)
        except Exception:
            pass  # never expose SMTP errors to clients

    return {"ok": True}
