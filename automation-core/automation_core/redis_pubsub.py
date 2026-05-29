import asyncio
import json
from typing import Any

import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError

from automation_core.settings import Settings


class RedisPubSubSubscriber:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis = self._create_redis_connection()
        self.pubsub = None

    def _create_redis_connection(self):
        return redis.from_url(
            self.settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_timeout=30,
            health_check_interval=30,
            retry_on_timeout=True,
        )

    async def subscribe(self) -> None:
        if self.pubsub is not None:
            return

        self.pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
        await self.pubsub.subscribe(self.settings.resolved_pubsub_channel)

    async def _reconnect(self) -> None:
        try:
            if self.pubsub is not None:
                await self.pubsub.aclose()
        except Exception:
            pass

        try:
            await self.redis.aclose()
        except Exception:
            pass

        await asyncio.sleep(self.settings.redis_reconnect_sleep_seconds)

        self.redis = self._create_redis_connection()
        self.pubsub = None
        await self.subscribe()

    async def close(self) -> None:
        if self.pubsub is not None:
            try:
                await self.pubsub.unsubscribe(self.settings.resolved_pubsub_channel)
            finally:
                await self.pubsub.aclose()

        await self.redis.aclose()

    async def read(self) -> list[dict[str, Any]]:
        await self.subscribe()

        try:
            message = await self.pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=self.settings.pubsub_poll_timeout_seconds,
            )
        except (TimeoutError, ConnectionError) as exc:
            print(
                {
                    "warning": "redis_pubsub_connection_error",
                    "error": str(exc),
                }
            )
            await self._reconnect()
            return []

        if not message:
            return []

        if message.get("type") != "message":
            return []

        payload_raw = message.get("data")

        if payload_raw is None:
            return []

        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            payload = {
                "event": "raw",
                "raw_payload": payload_raw,
            }

        return [payload]
