import os
import smtplib
import logging
from email.message import EmailMessage
from typing import Any, Optional


logger = logging.getLogger(__name__)


def _is_email_configured() -> bool:
    required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD"]
    return all(os.getenv(key) for key in required)


def _display_name(user: Any, fallback: str = "User") -> str:
    if user is None:
        return fallback
    return getattr(user, "full_name", None) or getattr(user, "name", None) or fallback


def _email_address(user: Any, fallback: Optional[str] = None) -> Optional[str]:
    if user is None:
        return fallback
    return getattr(user, "email", None) or fallback


def _send_email(to_email: Optional[str], subject: str, body: str, reply_to: Optional[str] = None) -> bool:
    if not to_email or not _is_email_configured():
        if not to_email:
            logger.warning("Email skipped: recipient address is missing")
        else:
            logger.warning("Email skipped: SMTP environment variables are incomplete")
        return False

    smtp_host = (os.getenv("SMTP_HOST") or "").strip()
    smtp_port = int((os.getenv("SMTP_PORT", "587") or "587").strip())
    smtp_username = (os.getenv("SMTP_USERNAME") or "").strip()
    smtp_password = (os.getenv("SMTP_PASSWORD") or "").strip()
    mail_from = (os.getenv("MAIL_FROM") or smtp_username).strip()
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() == "true"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = to_email
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)

    try:
        smtp_client = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        with smtp_client(smtp_host, smtp_port, timeout=20) as server:
            if os.getenv("SMTP_DEBUG", "false").lower() == "true":
                server.set_debuglevel(1)
            if use_tls and not use_ssl:
                server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        return True
    except Exception as exc:
        logger.exception("Failed to send email via SMTP: %s", exc)
        return False


def send_login_notification_email(to_email: str, full_name: str) -> bool:
    return _send_email(
        to_email,
        "Hamro Car Rental Login Notification",
        f"""Hi {full_name},

Your Hamro Car Rental account was just used to sign in successfully.

If this was not you, please reset your password immediately.

Thank you,
Hamro Car Rental Team
""",
    )


def send_account_created_email(to_email: str, full_name: str, role: str = "user") -> bool:
    return _send_email(
        to_email,
        "Welcome to Hamro Car Rental",
        f"""Hi {full_name},

Your Hamro Car Rental {role} account is ready.

You can now sign in and use the platform.

Thank you,
Hamro Car Rental Team
""",
    )


def send_password_reset_email(to_email: str, full_name: str, reset_url: str) -> bool:
    return _send_email(
        to_email,
        "Hamro Car Rental Password Reset",
        f"""Hi {full_name},

We received a request to reset your Hamro Car Rental password.

Reset your password using this link:
{reset_url}

This link expires in 30 minutes.

If you did not request this, you can safely ignore this email.

Thank you,
Hamro Car Rental Team
""",
    )


def _booking_summary_lines(booking: Any, post: Any) -> list[str]:
    return [
        f"Booking ID: {getattr(booking, 'id', 'N/A')}",
        f"Vehicle: {getattr(post, 'post_title', 'N/A')}",
        f"Pickup: {getattr(booking, 'pickup_location', 'N/A')}",
        f"Return: {getattr(booking, 'return_location', 'N/A')}",
        f"Dates: {getattr(booking, 'start_date', 'N/A')} to {getattr(booking, 'end_date', 'N/A')}",
        f"Status: {getattr(booking, 'status', 'N/A')}",
    ]


def send_booking_created_email(renter: Any, owner: Any, booking: Any, post: Any) -> bool:
    renter_email = _email_address(renter)
    owner_email = _email_address(owner)
    renter_name = _display_name(renter, "Renter")
    owner_name = _display_name(owner, "Owner")
    summary = "\n".join(_booking_summary_lines(booking, post))

    renter_sent = _send_email(
        renter_email,
        "Booking request received",
        f"""Hi {renter_name},

Your booking request has been created successfully.

{summary}

We will notify you when the booking changes status.

Thank you,
Hamro Car Rental Team
""",
    )
    owner_sent = _send_email(
        owner_email,
        "New booking request",
        f"""Hi {owner_name},

A new booking request has been created for your vehicle.

{summary}

Please review it in the dashboard.

Thank you,
Hamro Car Rental Team
""",
    )
    return renter_sent or owner_sent


def send_booking_status_updated_email(renter: Any, owner: Any, booking: Any, new_status: str, post: Any = None) -> bool:
    renter_email = _email_address(renter)
    owner_email = _email_address(owner)
    renter_name = _display_name(renter, "Renter")
    owner_name = _display_name(owner, "Owner")
    summary = "\n".join(_booking_summary_lines(booking, post or getattr(booking, "post", None)))

    renter_sent = _send_email(
        renter_email,
        f"Booking {new_status} notification",
        f"""Hi {renter_name},

Your booking status has been updated to: {new_status}.

{summary}

Thank you,
Hamro Car Rental Team
""",
    )
    owner_sent = _send_email(
        owner_email,
        f"Booking {new_status} notification",
        f"""Hi {owner_name},

A booking on your vehicle was updated to: {new_status}.

{summary}

Thank you,
Hamro Car Rental Team
""",
    )
    return renter_sent or owner_sent


def send_booking_cancelled_email(renter: Any, owner: Any, booking: Any, cancelled_by: Any, post: Any = None) -> bool:
    renter_email = _email_address(renter)
    owner_email = _email_address(owner)
    renter_name = _display_name(renter, "Renter")
    owner_name = _display_name(owner, "Owner")
    cancelled_by_name = _display_name(cancelled_by, "Someone")
    summary = "\n".join(_booking_summary_lines(booking, post or getattr(booking, "post", None)))

    renter_sent = _send_email(
        renter_email,
        "Booking cancelled",
        f"""Hi {renter_name},

Your booking has been cancelled by {cancelled_by_name}.

{summary}

Thank you,
Hamro Car Rental Team
""",
    )
    owner_sent = _send_email(
        owner_email,
        "Booking cancelled",
        f"""Hi {owner_name},

The booking has been cancelled by {cancelled_by_name}.

{summary}

Thank you,
Hamro Car Rental Team
""",
    )
    return renter_sent or owner_sent


def send_hire_request_created_email(requester: Any, owner: Any, hire_request: Any, post: Any) -> bool:
    requester_email = _email_address(requester)
    owner_email = _email_address(owner)
    requester_name = _display_name(requester, "Requester")
    owner_name = _display_name(owner, "Owner")
    summary = [
        f"Hire Request ID: {getattr(hire_request, 'id', 'N/A')}",
        f"Vehicle: {getattr(post, 'post_title', 'N/A')}",
        f"Pickup: {getattr(hire_request, 'pickup_location', 'N/A')}",
        f"Return: {getattr(hire_request, 'return_location', 'N/A')}",
        f"Dates: {getattr(hire_request, 'start_date', 'N/A')} to {getattr(hire_request, 'end_date', 'N/A')}",
        f"Status: {getattr(hire_request, 'status', 'N/A')}",
    ]
    summary_text = "\n".join(summary)

    requester_sent = _send_email(
        requester_email,
        "Hire request received",
        f"""Hi {requester_name},

Your hire request has been created successfully.

{summary_text}

We will notify you when the request is reviewed.

Thank you,
Hamro Car Rental Team
""",
    )
    owner_sent = _send_email(
        owner_email,
        "New hire request",
        f"""Hi {owner_name},

A new hire request has been created for your vehicle.

{summary_text}

Please review it in the dashboard.

Thank you,
Hamro Car Rental Team
""",
    )
    return requester_sent or owner_sent


def send_hire_request_status_updated_email(
    requester: Any,
    owner: Any,
    hire_request: Any,
    new_status: str,
    rejection_reason: Optional[str] = None,
) -> bool:
    requester_email = _email_address(requester)
    owner_email = _email_address(owner)
    requester_name = _display_name(requester, "Requester")
    owner_name = _display_name(owner, "Owner")
    summary = [
        f"Hire Request ID: {getattr(hire_request, 'id', 'N/A')}",
        f"Vehicle: {getattr(hire_request, 'vehicle_name', 'N/A')}",
        f"Pickup: {getattr(hire_request, 'pickup_location', 'N/A')}",
        f"Return: {getattr(hire_request, 'return_location', 'N/A')}",
        f"Dates: {getattr(hire_request, 'start_date', 'N/A')} to {getattr(hire_request, 'end_date', 'N/A')}",
        f"Status: {new_status}",
    ]
    if rejection_reason:
        summary.append(f"Reason: {rejection_reason}")
    summary_text = "\n".join(summary)

    requester_sent = _send_email(
        requester_email,
        f"Hire request {new_status}",
        f"""Hi {requester_name},

Your hire request status has been updated to: {new_status}.

{summary_text}

Thank you,
Hamro Car Rental Team
""",
    )
    owner_sent = _send_email(
        owner_email,
        f"Hire request {new_status}",
        f"""Hi {owner_name},

A hire request on your vehicle was updated to: {new_status}.

{summary_text}

Thank you,
Hamro Car Rental Team
""",
    )
    return requester_sent or owner_sent


def send_contact_received_email(contact: Any) -> bool:
    full_name = getattr(contact, "full_name", "Customer")
    email = getattr(contact, "email", None)
    subject = "We received your message"
    body = f"""Hi {full_name},

We received your contact message and will get back to you soon.

Subject: {getattr(contact, 'subject', 'N/A')}
Topic: {getattr(contact, 'topic', 'N/A')}

Thank you,
Hamro Car Rental Team
"""
    return _send_email(email, subject, body)


def send_contact_notification_email(contact: Any) -> bool:
    admin_email = os.getenv("ADMIN_EMAIL") or os.getenv("MAIL_TO") or os.getenv("MAIL_FROM")
    reply_to = getattr(contact, "email", None)
    subject = f"Contact message: {getattr(contact, 'subject', 'N/A')}"
    body = f"""A new contact message was submitted.

Name: {getattr(contact, 'full_name', 'N/A')}
Email: {getattr(contact, 'email', 'N/A')}
Phone: {getattr(contact, 'phone_number', 'N/A')}
Topic: {getattr(contact, 'topic', 'N/A')}
Subject: {getattr(contact, 'subject', 'N/A')}

Message:
{getattr(contact, 'message', 'N/A')}
"""
    return _send_email(admin_email, subject, body, reply_to=reply_to)


# Backward-compatible alias used by the existing auth router.
def send_account_created_login_email(to_email: str, full_name: str) -> bool:
    return send_login_notification_email(to_email, full_name)