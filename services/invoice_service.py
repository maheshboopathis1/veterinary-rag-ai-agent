#services/invioce_service.py
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException

from services.database import get_products_by_ids
from services.email_service import (
    create_invoice_html,
    send_html_email,
)


def send_invoice(
    customer_name: str,
    user_email: str,
    product_ids: list[str],
) -> dict:

    # Remove duplicate product IDs while preserving order.
    unique_product_ids = list(
    dict.fromkeys(str(pid).strip() for pid in product_ids)
)

    if not unique_product_ids:
        raise HTTPException(
            status_code=400,
            detail="No recommended products were provided.",
        )

    # 1. Retrieve the actual product records from MySQL.
    products = get_products_by_ids(unique_product_ids)

    if not products:
        raise HTTPException(
            status_code=404,
            detail="No recommended products were found.",
        )

    # 2. Generate a unique invoice reference.
    invoice_number = f"INV-{uuid4().hex[:12].upper()}"

    # 3. Create the HTML invoice email.
    html = create_invoice_html(
        invoice_number=invoice_number,
        invoice_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        customer_name=customer_name,
        user_email=user_email,
        products=products,
    )

    # 4. Send the email through the email service.
    try:
        print("proces to send",user_email,html,invoice_number)
        email_id = send_html_email(
            recipient_email=user_email,
            subject=f"Veterinary Product Invoice - {invoice_number}",
            html_body=html,
        )

        return {
            "status": "success",
            "message": "Invoice email submitted successfully.",
            "invoice_number": invoice_number,
            "email_id": email_id,
        }

    except Exception:
        # Log the detailed error inside email_service.py.
        raise HTTPException(
            status_code=502,
            detail="Unable to send invoice email.",
        )
