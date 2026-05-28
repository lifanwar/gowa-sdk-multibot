from dataclasses import dataclass
from typing import Any

from automation_core.message import IncomingMessage


@dataclass
class StartedEv:
    bot_name: str
    device_id: str
    stream_name: str


@dataclass
class MessageEv:
    event_id: str
    redis_stream_id: str
    device_id: str
    message: IncomingMessage
    raw: dict[str, Any]