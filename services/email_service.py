
import logging
from html import escape

import resend

from config import SENDER_EMAIL, RESEND_API_KEY

logger = logging.getLogger(__name__)

# Initialize Resend once when this module is imported.
resend.api_key = RESEND_API_KEY


def create_invoice_html(
    invoice_number: str,
    invoice_date: str,
    customer_name: str,
    user_email: str,
    products: list[dict],
) -> str:
    """
    Build an HTML invoice containing product information
    retrieved from the MySQL products table.
    """

    product_rows = ""
    product_details = ""

    for product in products:
        product_id = escape(str(product.get("ProductID") or "N/A"))
        ingredient = escape(
            str(product.get("ActiveIngredient") or "N/A")
        )
        category = escape(
            str(product.get("ProductCategory") or "N/A")
        )
        target_animal = escape(
            str(product.get("TargetAnimal") or "N/A")
        )
        disease = escape(str(product.get("Disease") or "N/A"))

        product_rows += f"""
        <tr>
            <td style="padding:10px;border:1px solid #ddd;">
                {product_id}
            </td>
            <td style="padding:10px;border:1px solid #ddd;">
                {ingredient}
            </td>
            <td style="padding:10px;border:1px solid #ddd;">
                {category}
            </td>
            <td style="padding:10px;border:1px solid #ddd;">
                {target_animal}
            </td>
            <td style="padding:10px;border:1px solid #ddd;">
                {disease}
            </td>
        </tr>
        """

        symptoms = escape(str(product.get("Symptoms") or "N/A"))
        dosage = escape(str(product.get("Dosage") or "N/A"))
        route = escape(
            str(product.get("RouteOfAdministration") or "N/A")
        )
        duration = escape(str(product.get("Duration") or "N/A"))
        precautions = escape(
            str(product.get("Precautions") or "N/A")
        )

        product_details += f"""
        <div style="
            margin:16px 0;
            padding:15px;
            border:1px solid #e5e7eb;
            border-radius:6px;
        ">
            <h3 style="color:#2c3e50;">
                Product ID: {product_id}
            </h3>

            <p><b>Active Ingredient:</b> {ingredient}</p>
            <p><b>Target Animal:</b> {target_animal}</p>
            <p><b>Disease:</b> {disease}</p>
            <p><b>Symptoms in Reference Data:</b> {symptoms}</p>
            <p><b>Dosage in Reference Data:</b> {dosage}</p>
            <p><b>Route of Administration:</b> {route}</p>
            <p><b>Duration in Reference Data:</b> {duration}</p>
            <p><b>Precautions:</b> {precautions}</p>
        </div>
        """

    safe_invoice_number = escape(invoice_number)
    safe_invoice_date = escape(invoice_date)
    safe_customer_name = escape(customer_name)
    safe_user_email = escape(user_email)

    # Required end-of-email notice.
    reference_notice = """
    <div style="
        margin-top:25px;
        padding:16px;
        background:#fff8e8;
        border-left:4px solid #d9a441;
        color:#59451b;
    ">
        <h3>Important Notice</h3>

        <p>
            Product recommendations are based on our currently
            available product data and reference documentation.
            Please consult a licensed veterinarian to confirm product
            suitability and treatment decisions.
        </p>

        <p>
            Product information in this email is provided for
            reference purposes and may not cover every animal's
            individual needs.
        </p>
    </div>
    """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Veterinary Product Invoice</title>
    </head>

    <body style="
        margin:0;
        padding:20px;
        background:#f5f7fa;
        color:#333;
        font-family:Arial,sans-serif;
        line-height:1.6;
    ">
        <div style="
            max-width:800px;
            margin:auto;
            padding:25px;
            background:#fff;
            border:1px solid #e5e7eb;
            border-radius:8px;
        ">
            <div style="text-align:center;">
                <h1 style="color:#2c3e50;">Product Invoice</h1>
                <p>Veterinary Information Assistant</p>
            </div>

            <hr style="border:none;border-top:1px solid #eee;">

            <h3>Invoice Information</h3>

            <p>
                <b>Invoice Number:</b> {safe_invoice_number}<br>
                <b>Invoice Date (UTC):</b> {safe_invoice_date}
            </p>

            <h3>Customer Information</h3>

            <p>
                <b>Name:</b> {safe_customer_name}<br>
                <b>Email:</b> {safe_user_email}
            </p>

            <h3>Recommended Product Records</h3>

            <table style="
                width:100%;
                border-collapse:collapse;
                font-size:13px;
            ">
                <thead>
                    <tr style="background:#f1f5f9;">
                        <th style="padding:10px;border:1px solid #ddd;">
                            Product ID
                        </th>
                        <th style="padding:10px;border:1px solid #ddd;">
                            Active Ingredient
                        </th>
                        <th style="padding:10px;border:1px solid #ddd;">
                            Category
                        </th>
                        <th style="padding:10px;border:1px solid #ddd;">
                            Target Animal
                        </th>
                        <th style="padding:10px;border:1px solid #ddd;">
                            Disease
                        </th>
                    </tr>
                </thead>

                <tbody>
                    {product_rows}
                </tbody>
            </table>

            <h3 style="margin-top:25px;">
                Product Reference Details
            </h3>

            {product_details}

            <p style="margin-top:25px;">
                Hello {safe_customer_name},<br><br>
                Here are the product details associated with your
                consultation. Please review them carefully.
            </p>

            {reference_notice}

            <div style="
                margin-top:25px;
                padding-top:15px;
                border-top:1px solid #eee;
                text-align:center;
                font-size:12px;
                color:#777;
            ">
                This is an automatically generated email.
            </div>
        </div>
    </body>
    </html>
    """


def send_html_email(
    recipient_email: str,
    subject: str,
    html_body: str,
) -> str:
    """
    Submit an HTML email using Resend.
    Returns the email provider's ID.
    """

    try:
        response = resend.Emails.send({
            "from": SENDER_EMAIL,
            "to": [recipient_email],
            "subject": subject,
            "html": html_body,
        })

        email_id = response.get("id")

        if not email_id:
            raise RuntimeError(
                "Resend did not return an email ID."
            )

        logger.info(
            "Email submitted successfully. Recipient=%s ID=%s",
            recipient_email,
            email_id,
        )

        return email_id

    except Exception:
        logger.exception(
            "Failed to submit email to %s",
            recipient_email,
        )
        raise
