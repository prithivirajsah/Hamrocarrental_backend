import os
import smtplib
from email.message import EmailMessage

def _is_email_configured() -> bool:
    required = [
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "MAIL_FROM",
    ]
    return all(os.getenv(key) for key in required)


def send_account_created_login_email(to_email: str, full_name: str) -> bool:
    """
    Sends a login notification email with account-created wording.
    Returns True when email is sent, otherwise False.
    """
    if not _is_email_configured():
        # Skip safely when SMTP env vars are not set.
        return False

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    mail_from = os.getenv("MAIL_FROM")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    msg = EmailMessage()
    msg["Subject"] = "HamroRental Account Notification"
    msg["From"] = mail_from
    msg["To"] = to_email
    msg.set_content(
        f"""Hi {full_name},

Your HamroRental account has been created and a successful login was detected.

If this was not you, please reset your password immediately.

Thank you,
HamroRental Team
"""
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            if use_tls:
                server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        return True
    except Exception:
        # Avoid breaking login when email delivery fails.
        return False
