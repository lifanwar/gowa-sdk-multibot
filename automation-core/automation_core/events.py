from dataclasses import dataclass
from typing import Any

from automation_core.message import IncomingMessage


@dataclass
class StartedEv:
    bot_name: str
    device_id: str
    channel_name: str

    @property
    def stream_name(self) -> str:
        # Compatibility alias untuk kode lama yang masih membaca event.stream_name.
        return self.channel_name


@dataclass
class MessageEv:
    device_id: str
    message: IncomingMessage
    raw: dict[str, Any]
    event_name: str
    channel_name: str
    event_id: str | None = None
    redis_stream_id: str | None = None
