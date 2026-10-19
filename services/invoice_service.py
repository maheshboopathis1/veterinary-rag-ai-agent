# services/invoice_service.py
import logging
from datetime import datetime, timezone
from uuid import uuid4

from services.database import get_products_by_ids
from services.email_service import create_invoice_html, send_html_email

logger = logging.getLogger(__name__)


def send_invoice(user_email: str, product_ids: list[str]) -> dict:
    """
    Build and email an invoice. Needs only verified product IDs and a
    recipient email. Raises on any failure; returns success ONLY after
    the SMTP server accepted the message.
    """
    if not user_email or not product_ids:
        raise ValueError("Email and product IDs are required.")

    products = get_products_by_ids(product_ids)

    if not products:
        raise ValueError("No matching products found.")

    # Never silently drop a requested product.
    found = {str(p.get("ProductID")).strip().upper() for p in products}
    missing = [pid for pid in product_ids if str(pid).strip().upper() not in found]
    if missing:
        raise ValueError(
            f"These product IDs were not found in the catalog: {', '.join(missing)}"
        )

    invoice_number = f"INV-{uuid4().hex[:12].upper()}"

    html_body = create_invoice_html(
        invoice_number=invoice_number,
        invoice_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        user_email=user_email,
        products=products,
    )

    message_id = send_html_email(
        recipient_email=user_email,
        subject=f"Invoice {invoice_number}",
        html_body=html_body,  # <-- was html_content (the bug)
    )

    return {
        "status": "success",
        "message": f"Invoice email submitted successfully to {user_email}.",
        "invoice_number": invoice_number,
        "message_id": message_id,
    }
