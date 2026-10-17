import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "test")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "petanimals")

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
SENDER_EMAIL = os.getenv(
    "SENDER_EMAIL",
    "Veterinary Assistant <support@example.com>",
)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

if not all([GEMINI_API_KEY, COHERE_API_KEY, PINECONE_API_KEY]):
    raise RuntimeError("Missing Gemini, Cohere, or Pinecone API key.")

if not all([RESEND_API_KEY, DB_USER, DB_PASSWORD, DB_NAME]):
    raise RuntimeError("Missing Resend or MySQL configuration.")