# Veterinary RAG AI Agent

> **An AI assistant that retrieves evidence, verifies data, and completes real tasks, and tells you honestly when something fails.**

**Live app:** https://notifications-reprints-signals-therefore.trycloudflare.com

---

## The Problem

Veterinary guidance lives in long documents, product data lives in a separate database, and admin work such as invoicing happens somewhere else. A general-purpose chatbot cannot bridge these reliably: it can state unsupported facts, misread product requests, and report an action as done when the service actually failed.

## What It Does

| Capability | Description |
|---|---|
| **Knowledge retrieval (RAG)** | Answers veterinary questions from passages retrieved from reference documents |
| **Product intelligence** | Searches product records in plain language and verifies results against MySQL |
| **Workflow automation** | Generates an invoice for requested products and sends it by SMTP email |

This is an information and workflow tool. It does not replace a licensed veterinarian.

## Design Principles

1. **Evidence before answers.** Responses are grounded in retrieved documents.
2. **The database is the source of truth.** Product details never come from generated text.
3. **Honest failure reporting.** SMTP submission is never presented as guaranteed inbox delivery.
4. **Safe by construction.** Unsafe SQL is rejected by independent backend validation.
5. **Clear boundaries.** The system never invents dosages, prices, or product details.

## Architecture

```
Streamlit UI  ->  FastAPI backend  ->  Gemini agent
                                          |-- Cohere + Pinecone        (document retrieval)
                                          |-- AWS RDS MySQL            (product verification)
                                          |-- Invoice generator + SMTP (email delivery)
```

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend API | FastAPI |
| LLM and agent orchestration | Google Gemini |
| Embeddings | Cohere |
| Vector database | Pinecone |
| Product database | AWS RDS MySQL (loaded from CSV) |
| Email | SMTP |
| Hosting | AWS EC2 |

**Veterinary RAG pipeline:** PDF to Markdown, chunking, Cohere embeddings, Pinecone index, retrieval, grounded Gemini answer.

**Product catalog:** MySQL table `vet_clinic` with `ProductID`, `ActiveIngredient`, `ProductName`, `ProductCategory`, `TargetAnimal`, `Disease`, `Symptoms`, `Dosage`, `RouteOfAdministration`, `Duration`, `Precautions`.

**Invoice flow:** identify products, verify in MySQL, validate recipient email, generate invoice, submit via SMTP, report the real outcome.

## Example Interactions

```
User:  What are common signs of tick fever in dogs?
Agent: Answers from retrieved reference passages and states when evidence is limited.

User:  Show me products for dogs with skin infections.
Agent: Returns matching records verified against MySQL.

User:  Send an invoice for these products to owner@example.com
Agent: Verifies the products, generates the invoice, submits it via SMTP,
       and reports the actual result.
```

## Getting Started

### Prerequisites

- Python 3.10+
- API keys for Google Gemini, Cohere, and Pinecone
- A MySQL database (local or AWS RDS)
- SMTP account credentials

### Installation

```bash
git clone https://github.com/maheshboopathis1/veterinary-rag-ai-agent.git
cd veterinary-rag-ai-agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

Copy the example environment file and fill in your values. **Never commit `.env`.**

```bash
cp .env.example .env
```

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Google Gemini |
| `COHERE_API_KEY` | Embeddings |
| `PINECONE_API_KEY` | Vector database |
| `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | MySQL connection |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | Email delivery |

_Adjust names to match your actual `.env.example`._

### Run

```bash
# Backend
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
streamlit run app.py
```

_Adjust file names to match your project._

## Testing

External services are mocked in automated tests. Routine test runs never send real emails.

```bash
pytest
```

Covered scenarios include retrieval with relevant and insufficient context, empty product results, unsafe SQL rejection, invoice requests with missing email or unknown product IDs, SMTP failure and success, malformed tool arguments, and session isolation.

## Safety and Limitations

- Not a diagnostic or prescribing system.
- A product match does not establish medical suitability.
- Consult a licensed veterinarian for treatment decisions, especially for serious or urgent symptoms.
- Answer quality depends on the coverage of the reference documents and product catalog.


## Author

**Mahesh Boopathi**
GitHub: [@maheshboopathis1](https://github.com/maheshboopathis1)
