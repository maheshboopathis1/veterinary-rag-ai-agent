import json
import os

from redis.asyncio import Redis


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://127.0.0.1:6379/0",
)

REDIS_TTL_SECONDS = int(
    os.getenv("REDIS_TTL_SECONDS", "86400")
)

MAX_HISTORY_MESSAGES = int(
    os.getenv("REDIS_MAX_MESSAGES", "20")
)

redis_client = Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
)


def _history_key(session_id: str) -> str:
    return f"veterinary:session:{session_id}:history"


def _recommended_key(session_id: str) -> str:
    return f"veterinary:session:{session_id}:recommended_products"


def _selected_invoice_key(session_id: str) -> str:
    return f"veterinary:session:{session_id}:invoice_products"

def _feedback_key(session_id: str) -> str:
    return f"veterinary:session:{session_id}:feedback"


async def check_redis_connection() -> bool:
    return bool(await redis_client.ping())


async def get_conversation_messages(
    session_id: str,
) -> list[dict]:
    """Return recent conversation messages in chronological order."""

    key = _history_key(session_id)

    messages = await redis_client.lrange(key, 0, -1)

    return [json.loads(message) for message in messages]


async def get_conversation_history(
    session_id: str,
) -> str:
    """Format recent messages for the LLM prompt."""

    messages = await get_conversation_messages(session_id)

    return "\n".join(
        f"{'Pet Owner' if message['role'] == 'user' else 'Assistant'}: "
        f"{message['content']}"
        for message in messages
    )


async def save_conversation_turn(
    session_id: str,
    user_message: str,
    assistant_message: str,
) -> None:
    """Save both sides of a conversation turn to Redis."""

    key = _history_key(session_id)

    messages = [
        {
            "role": "user",
            "content": user_message,
        },
        {
            "role": "assistant",
            "content": assistant_message,
        },
    ]

    # Save both messages and enforce the history limit atomically.
    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.rpush(
            key,
            *[json.dumps(message) for message in messages],
        )
        pipe.ltrim(key, -MAX_HISTORY_MESSAGES, -1)
        pipe.expire(key, REDIS_TTL_SECONDS)
        await pipe.execute()


async def save_recommended_products(
    session_id: str,
    product_ids: list,
) -> None:
    key = _recommended_key(session_id)

    await redis_client.set(
        key,
        json.dumps(product_ids),
        ex=REDIS_TTL_SECONDS,
    )


async def get_recommended_products(
    session_id: str,
) -> list:
    value = await redis_client.get(
        _recommended_key(session_id)
    )

    return json.loads(value) if value else []


async def save_selected_invoice_products(
    session_id: str,
    product_ids: list,
) -> None:
    key = _selected_invoice_key(session_id)

    await redis_client.set(
        key,
        json.dumps(product_ids),
        ex=REDIS_TTL_SECONDS,
    )


async def get_selected_invoice_products(
    session_id: str,
) -> list:
    value = await redis_client.get(
        _selected_invoice_key(session_id)
    )

    return json.loads(value) if value else []

async def save_feedback(
    session_id: str,
    rating: str,
    message_excerpt: str = "",
    comment: str | None = None,
) -> None:
    key = _feedback_key(session_id)

    entry = {
        "rating": rating,
        "message_excerpt": message_excerpt,
        "comment": comment,
    }

    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.rpush(key, json.dumps(entry))
        pipe.expire(key, REDIS_TTL_SECONDS)
        await pipe.execute()

async def clear_conversation(session_id: str) -> None:
    """Delete this session's chat and associated product selections."""

    await redis_client.delete(
        _history_key(session_id),
        _recommended_key(session_id),
        _selected_invoice_key(session_id),
        _feedback_key(session_id),
    )


async def close_redis_connection() -> None:
    await redis_client.aclose()
