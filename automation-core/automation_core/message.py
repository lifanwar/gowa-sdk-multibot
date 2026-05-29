from dataclasses import dataclass
from typing import Any


@dataclass
class IncomingMessage:
    id: str | None
    text: str
    sender: str | None
    chat_id: str | None
    device_id: str
    is_group: bool
    raw: dict[str, Any]

    @property
    def is_from_me(self) -> bool:
        return bool(self.raw.get("is_from_me", False))

    @property
    def direction(self) -> str:
        value = self.raw.get("direction")
        if value:
            return str(value)

        return "outgoing" if self.is_from_me else "incoming"

    @property
    def contact_id(self) -> str | None:
        value = self.raw.get("contact_id")
        if value:
            return str(value)

        return self.chat_id or self.sender

    @property
    def replied_to_id(self) -> str | None:
        value = self.raw.get("replied_to_id")
        return str(value) if value else None

    @property
    def timestamp(self) -> str | None:
        value = self.raw.get("timestamp")
        return str(value) if value else None

    @property
    def media_type(self) -> str | None:
        value = self.raw.get("media_type")
        return str(value) if value else None

    @property
    def media_path(self) -> str | None:
        value = self.raw.get("media_path")
        return str(value) if value else None

    @property
    def image(self) -> str | None:
        if self.media_type == "image" and self.media_path:
            return self.media_path

        value = self.raw.get("image")
        return str(value) if value else None

    @property
    def has_media(self) -> bool:
        if self.media_type or self.media_path:
            return True

        return bool(
            self.raw.get("image")
            or self.raw.get("video")
            or self.raw.get("audio")
            or self.raw.get("document")
            or self.raw.get("sticker")
        )

    @property
    def original_webhook_payload(self) -> dict[str, Any] | None:
        value = self.raw.get("raw")
        return value if isinstance(value, dict) else None
