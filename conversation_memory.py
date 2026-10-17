
# conversation_memory.py

MAX_HISTORY_MESSAGES = 12
MAX_STORED_TURNS = 20

sessions: dict[str, dict] = {}


def get_session(session_id: str) -> dict:
    return sessions.setdefault(
        session_id,
        {
            "messages": [],
            "recommended_products": [],
            "customer_email": None,
            "customer_name": None,
        },
    )


def get_conversation_history(session_id: str) -> str:
    session = get_session(session_id)
    messages = session["messages"][-MAX_HISTORY_MESSAGES:]

    return "\n".join(
        line
        for item in messages
        for line in (
            f"Pet Owner: {item['user']}",
            f"Assistant: {item['assistant']}",
        )
    )


def save_conversation_turn(
    session_id: str,
    user_message: str,
    assistant_response: str,
):
    session = get_session(session_id)

    session["messages"].append({
        "user": user_message,
        "assistant": assistant_response,
    })

    session["messages"] = session["messages"][-MAX_STORED_TURNS:]


def save_recommended_products(
    session_id: str,
    products: list[dict],
):
    """
    Save the actual product candidates shown to the user.

    Each product should contain a verified product_id and product_name.
    Optional fields: description.
    """
    session = get_session(session_id)

    normalized = []
    seen_ids = set()

    for product in products:
        product_id = product.get("product_id")
        product_name = product.get("product_name")

        if product_id is None or not product_name:
            continue

        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            continue

        if product_id in seen_ids:
            continue

        seen_ids.add(product_id)

        normalized.append({
            "product_id": product_id,
            "product_name": str(product_name).strip(),
            "description": str(product.get("description", "")),
        })

    # Store the latest displayed recommendation set.
    # This makes "first product" refer to the latest displayed list.
    session["recommended_products"] = normalized


def get_recommended_products(session_id: str) -> list[dict]:
    session = get_session(session_id)
    return list(session.get("recommended_products", []))


def save_customer_details(
    session_id: str,
    email: str | None = None,
    customer_name: str | None = None,
):
    session = get_session(session_id)

    if email:
        session["customer_email"] = email.strip()

    if customer_name:
        session["customer_name"] = customer_name.strip()


def get_customer_details(session_id: str) -> dict:
    session = get_session(session_id)

    return {
        "customer_email": session.get("customer_email"),
        "customer_name": session.get("customer_name"),
    }


def save_verified_product_ids(
    session_id: str,
    product_ids: list[int],
):
    session = sessions.setdefault(session_id, {"messages": []})

    existing = session.get("verified_product_ids", [])
    session["verified_product_ids"] = list(
        dict.fromkeys(
            [int(pid) for pid in existing]
            + [int(pid) for pid in product_ids]
        )
    )


def get_verified_product_ids(session_id: str) -> list[int]:
    session = sessions.get(session_id, {})
    return session.get("verified_product_ids", [])


def save_selected_invoice_products(
    session_id: str,
    product_ids: list[int],
):
    session = sessions.setdefault(session_id, {"messages": []})

    # Replace the selection with the user's latest confirmed selection.
    session["selected_invoice_product_ids"] = list(
        dict.fromkeys(int(pid) for pid in product_ids)
    )


def get_selected_invoice_products(session_id: str) -> list[int]:
    session = sessions.get(session_id, {})
    return session.get("selected_invoice_product_ids", [])


