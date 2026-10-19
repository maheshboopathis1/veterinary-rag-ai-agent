from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=5000)


class ChatResponse(BaseModel):
    response: str
    source_used: str
    session_id: str
    invoice_sent: bool = False
    invoice_number: str | None = None
    invoice_email: str | None = None


class InvoiceRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    user_email: EmailStr


class FeedbackRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    rating: Literal["up", "down"]
    message_excerpt: str = Field(default="", max_length=500)
    comment: str | None = Field(default=None, max_length=1000)


class HistoryMessage(BaseModel):
    role: str
    content: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[HistoryMessage]
