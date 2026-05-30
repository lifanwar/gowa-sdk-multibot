import os
import redis

REDIS_URL = os.getenv("REDIS_URL")
DEVICE_ID = os.getenv("DEVICE_ID") or os.getenv("GOWA_DEVICE_ID")

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True
)

MEDIA_TTL_SECONDS = 2 * 24 * 60 * 60  # 2 hari


def _media_key(message_id) -> str:
    return f"{DEVICE_ID}:media:{message_id}"


def save_media_path_to_redis(message_id, media_path: str) -> bool:
    if not message_id:
        raise ValueError("Message ID tidak ditemukan")

    if not media_path:
        raise ValueError("Media path tidak ditemukan")

    key = _media_key(message_id)

    redis_client.setex(
        key,
        MEDIA_TTL_SECONDS,
        media_path
    )

    return True


def get_media_path_from_redis(message_id) -> str | None:
    if not message_id:
        raise ValueError("Message ID tidak ditemukan")

    key = _media_key(message_id)

    return redis_client.get(key)