from pydantic import BaseModel, EmailStr, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=5000)


class ChatResponse(BaseModel):
    response: str
    source_used: str
    session_id: str


class InvoiceRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    user_email: EmailStr
    customer_name: str = Field(min_length=1, max_length=200)
    product_ids: list[int] = Field(min_length=1, max_length=100)