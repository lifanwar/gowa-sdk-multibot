import asyncio
import inspect
from collections import defaultdict
from typing import Any, Callable, DefaultDict, Type

from automation_core.events import MessageEv, StartedEv
from automation_core.gowa_client import GowaClient
from automation_core.message import IncomingMessage
from automation_core.redis_stream import RedisStreamConsumer
from automation_core.settings import get_settings


Handler = Callable[..., Any]


class AutomationClient:
    def __init__(self):
        self.settings = get_settings()
        self.consumer = RedisStreamConsumer(self.settings)
        self.gowa = GowaClient(self.settings)
        self.handlers: DefaultDict[Type[Any], list[Handler]] = defaultdict(list)
        self.running = False

    def event(self, event_type: Type[Any]):
        def decorator(handler: Handler) -> Handler:
            self.handlers[event_type].append(handler)
            return handler

        return decorator

    async def emit(self, event: Any) -> None:
        event_type = type(event)

        for handler in self.handlers.get(event_type, []):
            result = handler(self, event)

            if inspect.isawaitable(result):
                await result

    def build_message_event(
        self,
        redis_stream_id: str,
        event: dict[str, Any],
    ) -> MessageEv:
        payload = event.get("payload") or {}
    
        message = IncomingMessage(
            id=payload.get("message_id") or payload.get("id"),
            text=payload.get("text") or payload.get("body") or "",
            sender=payload.get("sender") or payload.get("from"),
            chat_id=payload.get("chat_id"),
            device_id=payload.get("device_id") or self.settings.device_id,
            is_group=bool(
                payload.get("is_group")
                or str(payload.get("chat_id") or "").endswith("@g.us")
            ),
            raw=payload.get("raw") or payload,
        )
    
        return MessageEv(
            event_id=event.get("event_id") or "",
            redis_stream_id=redis_stream_id,
            device_id=message.device_id,
            message=message,
            raw=payload,
        )

    async def reply_message(
        self,
        text: str,
        message: IncomingMessage,
    ) -> dict[str, Any]:
        target = message.chat_id or message.sender

        if not target:
            raise ValueError("Cannot reply because chat_id and sender are empty")

        return await self.gowa.send_message(
            to=target,
            text=text,
            reply_message_id=message.id,
        )

    async def send_message(
        self,
        to: str,
        text: str,
        extra_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self.gowa.send_message(
            to=to,
            text=text,
            extra_payload=extra_payload,
        )

    async def start(self) -> None:
        await self.consumer.ensure_group()

        started_event = StartedEv(
            bot_name=self.settings.bot_name,
            device_id=self.settings.device_id,
            stream_name=self.settings.resolved_stream_name,
        )

        await self.emit(started_event)

        self.running = True

        while self.running:
            events = await self.consumer.read()

            if not events:
                continue

            for redis_stream_id, event in events:
                try:
                    message_event = self.build_message_event(
                        redis_stream_id=redis_stream_id,
                        event=event,
                    )

                    await self.emit(message_event)

                    if self.settings.ack_on_handler_success:
                        await self.consumer.ack(redis_stream_id)

                except Exception as exc:
                    print(
                        {
                            "error": str(exc),
                            "redis_stream_id": redis_stream_id,
                            "event": event,
                        }
                    )

    async def stop(self) -> None:
        self.running = False
        await self.consumer.close()
        await self.gowa.close()

    def run(self) -> None:
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            print("Worker stopped by user")