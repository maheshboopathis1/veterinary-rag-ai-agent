
# services/rag_service.py

import cohere
from pinecone import Pinecone

from config import (
    COHERE_API_KEY,
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
    PINECONE_NAMESPACE,
)

co_client = cohere.ClientV2(api_key=COHERE_API_KEY)
pc_client = Pinecone(api_key=PINECONE_API_KEY)
index_connection = pc_client.Index(PINECONE_INDEX_NAME)


def query_medical_rag_database_with_products(
    user_query: str,
) -> dict:
    embedding_response = co_client.embed(
        texts=[user_query],
        model="embed-english-v3.0",
        input_type="search_query",
        embedding_types=["float"],
    )

    query_vector = embedding_response.embeddings.float_[0]

    results = index_connection.query(
        namespace=PINECONE_NAMESPACE,
        vector=query_vector,
        top_k=3,
        include_metadata=True,
    )

    context_blocks = []
    products = []
    seen_ids = set()

    for match in results.matches:
        metadata = match.metadata or {}
        content = metadata.get("text", "")

        if content and content.strip():
            context_blocks.append(
                f"[Source: {metadata.get('source', 'Veterinary guideline')} "
                f"| Topic: {metadata.get('main_topic', 'Unknown')} "
                f"| Section: {metadata.get('sub_section', 'Unknown')}]\n"
                f"Content: {content}"
            )

        # Only treat records with explicit product metadata as products.
        product_id = metadata.get("product_id")
        product_name = metadata.get("product_name")

        if product_id is None or not product_name:
            continue

        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            continue

        if product_id in seen_ids:
            continue

        seen_ids.add(product_id)

        products.append({
            "product_id": product_id,
            "product_name": str(product_name),
            "description": str(content),
        })

    return {
        "context": "\n\n---\n\n".join(context_blocks),
        "products": products,
    }


def query_medical_rag_database(user_query: str) -> str:
    """
    Backward-compatible function for existing callers.
    """
    result = query_medical_rag_database_with_products(user_query)
    return result["context"]
