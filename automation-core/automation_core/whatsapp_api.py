from typing import Any
from urllib.parse import quote

import httpx

from automation_core.settings import Settings


class WhatsAppApi:
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

    def _extract_message_id(self, data: dict[str, Any]) -> str | None:
        results = data.get("results")
        if isinstance(results, dict):
            message_id = (
                results.get("message_id")
                or results.get("messageId")
                or results.get("id")
            )
            if message_id:
                return str(message_id)

        message_id = (
            data.get("message_id")
            or data.get("messageId")
            or data.get("id")
        )

        return str(message_id) if message_id else None

    def _normalize_response(self, data: dict[str, Any]) -> dict[str, Any]:
        message_id = self._extract_message_id(data)

        if message_id and "message_id" not in data:
            data["message_id"] = message_id

        return data

    async def _post(
        self,
        path: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        response = await self.client.post(
            path,
            json=payload,
        )
        response.raise_for_status()

        if response.content:
            data = response.json()

            if isinstance(data, dict):
                return self._normalize_response(data)

            return {
                "ok": True,
                "data": data,
            }

        return {"ok": True}

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
        if not to:
            raise ValueError("to is required")

        if not text:
            raise ValueError("text is required")

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

        return await self._post(
            self.settings.gowa_send_message_path,
            payload,
        )

    async def update_message(
        self,
        message_id: str,
        to: str,
        text: str,
    ) -> dict[str, Any]:
        if not message_id:
            raise ValueError("message_id is required")

        if not to:
            raise ValueError("to is required")

        if not text:
            raise ValueError("text is required")

        safe_message_id = quote(message_id, safe="")
        path = f"/message/{safe_message_id}/update"

        payload = {
            "phone": to,
            "message": text,
        }

        return await self._post(path, payload)
