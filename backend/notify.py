"""Email the admin when something is reported. Optional: set SMTP_HOST, SMTP_USER, SMTP_PASSWORD (and SMTP_FROM, SMTP_PORT).
Without them the report still appears in the admin page and is written to the log."""
import logging
import os
import smtplib
from email.message import EmailMessage

from starlette.concurrency import run_in_threadpool

log = logging.getLogger(__name__)


def admin_emails() -> list:
    return [e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()]


def _send(subject: str, body: str):
    host = os.environ.get("SMTP_HOST")
    to = admin_emails()
    if not host or not to:
        log.info("ADMIN ALERT (no SMTP configured): %s\n%s", subject, body)
        return
    msg = EmailMessage()
    msg["Subject"], msg["To"] = subject, ", ".join(to)
    msg["From"] = os.environ.get("SMTP_FROM") or os.environ.get("SMTP_USER") or to[0]
    msg.set_content(body)
    try:
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587")), timeout=15) as s:
            s.starttls()
            if os.environ.get("SMTP_USER"):
                s.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
            s.send_message(msg)
    except Exception as e:  # never let an email problem break a report
        log.warning("Could not send admin alert: %s", e)


async def alert_admin(subject: str, body: str):
    link = (os.environ.get("APP_URL") or "").rstrip("/")
    if link:
        body += f"\n\nReview it here: {link}/admin"
    await run_in_threadpool(_send, subject, body)
