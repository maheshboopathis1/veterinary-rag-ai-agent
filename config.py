import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "veterinary")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "petanimals")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
# Gmail shows App Passwords with spaces; they are not part of the password.
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip()

if not all([GEMINI_API_KEY, COHERE_API_KEY, PINECONE_API_KEY]):
    raise RuntimeError("Missing Gemini, Cohere, or Pinecone API key.")

if not all([DB_USER, DB_PASSWORD, DB_NAME]):
    raise RuntimeError("Missing MySQL configuration (DB_USER, DB_PASSWORD, DB_NAME).")
