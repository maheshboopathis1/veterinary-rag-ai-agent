# services/email_service.py
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from html import escape

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Email could not be sent. The message is safe to show to the model/user."""


_TD = "padding:10px;border:1px solid #ddd;"


def _v(product: dict, key: str) -> str:
    return escape(str(product.get(key) or "N/A"))


def create_invoice_html(
    invoice_number: str,
    invoice_date: str,
    user_email: str,
    products: list[dict],
) -> str:
    """Build the HTML invoice from MySQL product records."""

    rows = ""
    details = ""

    for p in products:
        pid = _v(p, "ProductID")
        ingredient = _v(p, "ActiveIngredient")
        target = _v(p, "TargetAnimal")
        disease = _v(p, "Disease")

        rows += f"""
        <tr>
            <td style="{_TD}">{pid}</td>
            <td style="{_TD}">{ingredient}</td>
            <td style="{_TD}">{_v(p, "ProductCategory")}</td>
            <td style="{_TD}">{target}</td>
            <td style="{_TD}">{disease}</td>
        </tr>
        """

        details += f"""
        <div style="margin:16px 0;padding:15px;border:1px solid #e5e7eb;border-radius:6px;">
            <h3 style="color:#2c3e50;">Product ID: {pid}</h3>
            <p><b>Active Ingredient:</b> {ingredient}</p>
            <p><b>Target Animal:</b> {target}</p>
            <p><b>Disease:</b> {disease}</p>
            <p><b>Symptoms in Reference Data:</b> {_v(p, "Symptoms")}</p>
            <p><b>Dosage in Reference Data:</b> {_v(p, "Dosage")}</p>
            <p><b>Route of Administration:</b> {_v(p, "RouteOfAdministration")}</p>
            <p><b>Duration in Reference Data:</b> {_v(p, "Duration")}</p>
            <p><b>Precautions:</b> {_v(p, "Precautions")}</p>
        </div>
        """

    safe_number = escape(invoice_number)
    safe_date = escape(invoice_date)
    safe_email = escape(user_email)

    th = f'style="{_TD}"'

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Veterinary Product Invoice</title>
    </head>
    <body style="margin:0;padding:20px;background:#f5f7fa;color:#333;
                 font-family:Arial,sans-serif;line-height:1.6;">
        <div style="max-width:800px;margin:auto;padding:25px;background:#fff;
                    border:1px solid #e5e7eb;border-radius:8px;">

            <div style="text-align:center;">
                <h1 style="color:#2c3e50;">Product Invoice</h1>
                <p>Veterinary Information Assistant</p>
            </div>

            <hr style="border:none;border-top:1px solid #eee;">

            <h3>Invoice Information</h3>
            <p>
                <b>Invoice Number:</b> {safe_number}<br>
                <b>Invoice Date (UTC):</b> {safe_date}<br>
                <b>Sent to:</b> {safe_email}
            </p>

            <h3>Product Records</h3>
            <table style="width:100%;border-collapse:collapse;font-size:13px;">
                <thead>
                    <tr style="background:#f1f5f9;">
                        <th {th}>Product ID</th>
                        <th {th}>Active Ingredient</th>
                        <th {th}>Category</th>
                        <th {th}>Target Animal</th>
                        <th {th}>Disease</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>

            <h3 style="margin-top:25px;">Product Reference Details</h3>
            {details}

            <p style="margin-top:25px;">
                Hello,<br><br>
                Here are the product details associated with your
                consultation. Please review them carefully.
            </p>

            <div style="margin-top:25px;padding:16px;background:#fff8e8;
                        border-left:4px solid #d9a441;color:#59451b;">
                <h3>Important Notice</h3>
                <p>
                    Product information is based on our currently available
                    product data and reference documentation. Please consult a
                    licensed veterinarian to confirm product suitability and
                    treatment decisions.
                </p>
                <p>
                    This information is provided for reference purposes and may
                    not cover every animal's individual needs.
                </p>
            </div>

            <div style="margin-top:25px;padding-top:15px;border-top:1px solid #eee;
                        text-align:center;font-size:12px;color:#777;">
                This is an automatically generated email.
            </div>
        </div>
    </body>
    </html>
    """


def _deliver(server: smtplib.SMTP, msg: EmailMessage, recipient: str) -> None:
    server.login(SMTP_USER, SMTP_PASSWORD)
    refused = server.send_message(msg)
    if refused:
        raise EmailDeliveryError(
            f"The mail server refused the recipient address: {recipient}"
        )


def send_html_email(
    recipient_email: str,
    subject: str,
    html_body: str,
) -> str:
    """
    Send an HTML email over SMTP.
    Returns the Message-ID once the SMTP server has accepted the message.
    Raises EmailDeliveryError on ANY failure (never returns on failure).
    """

    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        raise EmailDeliveryError(
            "Email service is not configured "
            "(SMTP_HOST, SMTP_USER, SMTP_PASSWORD)."
        )

    recipient = (recipient_email or "").strip()
    if not recipient or "@" not in recipient:
        raise EmailDeliveryError("A valid recipient email address is required.")

    sender_domain = SMTP_USER.split("@")[-1] if "@" in SMTP_USER else None
    message_id = make_msgid(domain=sender_domain)

    msg = EmailMessage()
    msg["From"] = formataddr(("Veterinary AI", SMTP_USER))
    msg["To"] = recipient
    msg["Subject"] = subject
    msg["Message-ID"] = message_id
    msg.set_content(
        "Please open this email in an HTML-compatible email client "
        "to view the veterinary invoice."
    )
    msg.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()

    try:
        if SMTP_PORT == 465:
            # Implicit SSL
            with smtplib.SMTP_SSL(
                SMTP_HOST, SMTP_PORT, timeout=30, context=context
            ) as server:
                _deliver(server, msg, recipient)
        else:
            # STARTTLS (587 and others)
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                _deliver(server, msg, recipient)

    except EmailDeliveryError:
        logger.exception("SMTP delivery failed for %s", recipient)
        raise
    except smtplib.SMTPAuthenticationError as exc:
        logger.exception("SMTP authentication failed")
        raise EmailDeliveryError(
            "SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD "
            "(Gmail requires an App Password)."
        ) from exc
    except smtplib.SMTPRecipientsRefused as exc:
        logger.exception("SMTP recipient refused")
        raise EmailDeliveryError(
            f"The mail server refused the recipient address: {recipient}"
        ) from exc
    except (smtplib.SMTPException, OSError) as exc:
        logger.exception("SMTP connection/send error")
        raise EmailDeliveryError(
            "Could not connect to or send through the SMTP server."
        ) from exc

    logger.info("Email accepted by SMTP server for %s", recipient)
    return message_id
