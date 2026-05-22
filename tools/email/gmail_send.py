"""Gmail SMTP sender. Requires GMAIL_USER + GMAIL_APP_PASSWORD in .env."""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


class GmailSendError(RuntimeError):
    pass


def send(
    to_address: str,
    subject: str,
    body_text: str,
    from_name: str = "Harsh Patadia",
    reply_to: str | None = None,
) -> dict:
    user = os.getenv("GMAIL_USER")
    app_pwd = os.getenv("GMAIL_APP_PASSWORD")
    if not user or not app_pwd:
        raise GmailSendError("GMAIL_USER / GMAIL_APP_PASSWORD missing in .env")

    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((from_name, user))
    msg["To"] = to_address
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(user, app_pwd)
        smtp.send_message(msg)

    logger.info("sent email to %s subject=%r", to_address, subject)
    return {"to": to_address, "subject": subject, "from": user}
