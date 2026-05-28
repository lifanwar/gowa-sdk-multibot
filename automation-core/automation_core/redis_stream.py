import json
from typing import Any

import redis.asyncio as redis
from redis.exceptions import ConnectionError, ResponseError, TimeoutError

from automation_core.settings import Settings


class RedisStreamConsumer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis = self._create_redis_connection()

    def _create_redis_connection(self):
        return redis.from_url(
            self.settings.redis_url,
            decode_responses=True,

            # Penting untuk Redis Cloud agar koneksi tidak mudah putus
            # saat XREADGROUP memakai blocking read.
            socket_connect_timeout=10,
            socket_timeout=30,
            health_check_interval=30,
            retry_on_timeout=True,
        )

    async def close(self) -> None:
        await self.redis.aclose()

    async def ensure_group(self) -> None:
        try:
            await self.redis.xgroup_create(
                name=self.settings.resolved_stream_name,
                groupname=self.settings.resolved_consumer_group,
                id="0",
                mkstream=True,
            )
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def read(self) -> list[tuple[str, dict[str, Any]]]:
        try:
            response = await self.redis.xreadgroup(
                groupname=self.settings.resolved_consumer_group,
                consumername=self.settings.resolved_consumer_name,
                streams={
                    self.settings.resolved_stream_name: ">",
                },
                count=self.settings.stream_count,
                block=self.settings.stream_block_ms,
            )

        except TimeoutError:
            # Timeout saat blocking read bukan error fatal.
            # Artinya belum ada event baru atau Redis Cloud menutup read setelah batas tertentu.
            return []

        except ConnectionError as exc:
            print(
                {
                    "warning": "redis_connection_error",
                    "error": str(exc),
                }
            )

            await self.redis.aclose()
            self.redis = self._create_redis_connection()
            return []

        events: list[tuple[str, dict[str, Any]]] = []

        if not response:
            return events

        for _, messages in response:
            for redis_stream_id, fields in messages:
                payload_raw = fields.get("payload", "{}")

                try:
                    payload = json.loads(payload_raw)
                except json.JSONDecodeError:
                    payload = {
                        "raw_payload": payload_raw,
                    }

                event = {
                    "event_id": fields.get("event_id"),
                    "payload": payload,
                }

                events.append((redis_stream_id, event))

        return events

    async def ack(self, redis_stream_id: str) -> None:
        await self.redis.xack(
            self.settings.resolved_stream_name,
            self.settings.resolved_consumer_group,
            redis_stream_id,
        )