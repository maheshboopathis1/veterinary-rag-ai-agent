#app.py
import logging
import asyncio

from fastapi import FastAPI, HTTPException

from models import ChatRequest, ChatResponse, InvoiceRequest
from conversation_memory import (
    get_recommended_products,
    save_conversation_turn,
    get_conversation_history,
)
from services.rag_service import query_medical_rag_database
from services.chat_service import generate_chat_response
from services.invoice_service import send_invoice
from conversation_memory import get_selected_invoice_products


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Veterinary AI RAG Chatbot")


@app.post("/chat", response_model=ChatResponse)
async def process_chatbot_turn(payload: ChatRequest):
    session_id = payload.session_id.strip()
    user_input = payload.message.strip()

    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="Session ID is required.",
        )

    if not user_input:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    # 1. Load earlier conversation.
    history = get_conversation_history(session_id)

    # 2. Retrieve relevant veterinary knowledge.
    rag_query = (
        f"Conversation history:\n{history[-1500:]}\n\n"
        f"Current user request:\n{user_input}"
    )

    rag_results = await asyncio.to_thread(
        query_medical_rag_database,
        rag_query,
    )

    print("Coming RAG result:", rag_results)

    # Your RAG service currently returns a list of strings.
    if isinstance(rag_results, str):
        rag_context = rag_results

    elif isinstance(rag_results, list):
        rag_context = "\n\n".join(
            str(item.get("text", ""))
            if isinstance(item, dict)
            else str(item)
            for item in rag_results
            if item
        )

    else:
        rag_context = ""

    print("Formatted RAG context:", rag_context)

    # 3. Gemini answers or orchestrates the SQL/invoice tools.
    response_text = await generate_chat_response(
        user_input=user_input,
        history=history,
        rag_context=rag_context,
    )

    # 4. Save this completed conversation turn.
    save_conversation_turn(
        session_id=session_id,
        user_message=user_input,
        assistant_response=response_text,
    )

    return ChatResponse(
        response=response_text,
        source_used="RAG and Gemini tools",
        session_id=session_id,
    )


@app.post("/send-invoice")
def trigger_invoice(payload: InvoiceRequest):
    session_id = payload.session_id.strip()

    selected_ids = get_selected_invoice_products(session_id)

    if not selected_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "No user-confirmed products are available for invoicing. "
                "Please select and confirm the products in the chat first."
            ),
        )

    result = send_invoice(
        customer_name=payload.customer_name,
        user_email=str(payload.user_email),
        product_ids=selected_ids,
    )

    return {
        "message": result.get(
            "message",
            "Invoice request processed.",
        ),
        "session_id": session_id,
        **result,
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}