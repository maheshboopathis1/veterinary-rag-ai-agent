#app.py
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from models import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    HistoryResponse,
    InvoiceRequest,
)

from conversation_memory import (
    check_redis_connection,
    close_redis_connection,
    get_conversation_history,
    get_conversation_messages,
    get_selected_invoice_products,
    save_conversation_turn,
    save_feedback,
)

from services.chat_service import generate_chat_response
from services.invoice_service import send_invoice
from services.email_service import EmailDeliveryError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await check_redis_connection()
    logger.info("Redis connected successfully.")
    yield
    await close_redis_connection()


app = FastAPI(lifespan=lifespan, title="Veterinary AI Agent")


@app.get("/")
async def root_check():
    return "success"


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def process_chatbot_turn(payload: ChatRequest):
    session_id = payload.session_id.strip()
    user_input = payload.message.strip()

    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required.")

    if not user_input:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        history = await get_conversation_history(session_id)

        invoice_state: dict = {}

        response_text = await generate_chat_response(
            user_input=user_input,
            history=history,
            invoice_state=invoice_state,
        )

        await save_conversation_turn(
            session_id=session_id,
            user_message=user_input,
            assistant_message=response_text,
        )

        return ChatResponse(
            response=response_text,
            source_used="Gemini tools",
            session_id=session_id,
            invoice_sent=bool(invoice_state.get("sent")),
            invoice_number=invoice_state.get("invoice_number"),
            invoice_email=invoice_state.get("email"),
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Chat processing error")
        raise HTTPException(
            status_code=500,
            detail="Unable to process your message. Please try again.",
        ) from exc

@app.get("/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str):
    session_id = session_id.strip()

    if not session_id or len(session_id) > 100:
        raise HTTPException(status_code=400, detail="Invalid session ID.")

    messages = await get_conversation_messages(session_id)

    return HistoryResponse(session_id=session_id, messages=messages)


@app.post("/feedback")
async def submit_feedback(payload: FeedbackRequest):
    await save_feedback(
        session_id=payload.session_id.strip(),
        rating=payload.rating,
        message_excerpt=payload.message_excerpt,
        comment=payload.comment,
    )
    return {"status": "saved"}

@app.post("/send-invoice")
async def trigger_invoice(payload: InvoiceRequest):
    session_id = payload.session_id.strip()

    selected_ids = await get_selected_invoice_products(session_id)

    if not selected_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "No user-confirmed products are available for invoicing. "
                "Please select and confirm the products in the chat first."
            ),
        )

    try:
        result = await asyncio.to_thread(
            send_invoice,
            user_email=str(payload.user_email),
            product_ids=selected_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EmailDeliveryError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Invoice endpoint failed")
        raise HTTPException(status_code=500, detail="Invoice could not be sent.") from exc

    return {"session_id": session_id, **result}
