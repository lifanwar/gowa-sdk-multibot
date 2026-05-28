from typing import Any

import httpx

from automation_core.settings import Settings


class GowaClient:
    def __init__(self, settings: Settings):
        self.settings = settings

        auth = None
        if settings.gowa_basic_auth_username and settings.gowa_basic_auth_password:
            auth = (
                settings.gowa_basic_auth_username,
                settings.gowa_basic_auth_password,
            )

        self.client = httpx.AsyncClient(
            base_url=settings.gowa_base_url.rstrip("/"),
            timeout=30,
            auth=auth,
            headers={
                "X-Device-Id": settings.resolved_gowa_device_id,
            },
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def send_message(
        self,
        to: str,
        text: str,
        reply_message_id: str | None = None,
        is_forwarded: bool | None = None,
        duration: int | None = None,
        mentions: list[str] | None = None,
        extra_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "phone": to,
            "message": text,
        }

        if reply_message_id:
            payload["reply_message_id"] = reply_message_id

        if is_forwarded is not None:
            payload["is_forwarded"] = is_forwarded

        if duration is not None:
            payload["duration"] = duration

        if mentions:
            payload["mentions"] = mentions

        if extra_payload:
            payload.update(extra_payload)

        response = await self.client.post(
            self.settings.gowa_send_message_path,
            json=payload,
        )
        response.raise_for_status()

        if response.content:
            return response.json()

        return {
            "ok": True,
        }