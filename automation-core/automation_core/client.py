import asyncio
import inspect
from collections import defaultdict
from typing import Any, Callable, DefaultDict, Type

from automation_core.events import MessageEv, StartedEv
from automation_core.message import IncomingMessage
from automation_core.redis_pubsub import RedisPubSubSubscriber
from automation_core.settings import get_settings
from automation_core.whatsapp_api import WhatsAppApi


Handler = Callable[..., Any]


class AutomationClient:
    def __init__(self):
        self.settings = get_settings()
        self.subscriber = RedisPubSubSubscriber(self.settings)
        self._whatsapp = WhatsAppApi(self.settings)
        self.handlers: DefaultDict[Type[Any], list[Handler]] = defaultdict(list)
        self.running = False
        self._stopping = False

    def __getattr__(self, name: str):
        whatsapp = self.__dict__.get("_whatsapp")

        if whatsapp is not None and hasattr(whatsapp, name):
            return getattr(whatsapp, name)

        raise AttributeError(
            f"{self.__class__.__name__!s} object has no attribute {name!r}"
        )

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
        payload: dict[str, Any],
    ) -> MessageEv:
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
            # Simpan payload normalized sebagai raw agar property seperti
            # is_from_me, direction, media_type, dan media_path tetap benar.
            raw=payload,
        )

        return MessageEv(
            event_id=payload.get("event_id") or payload.get("message_id") or payload.get("id"),
            device_id=message.device_id,
            message=message,
            raw=payload,
            event_name=str(payload.get("event") or "message"),
            channel_name=self.settings.resolved_pubsub_channel,
        )

    async def reply_message(
        self,
        text: str,
        message: IncomingMessage,
    ) -> dict[str, Any]:
        target = message.contact_id

        if not target:
            raise ValueError("Cannot reply because message contact_id is empty")

        return await self._whatsapp.send_message(
            to=target,
            text=text,
            reply_message_id=message.id,
        )

    async def start(self) -> None:
        await self.subscriber.subscribe()

        started_event = StartedEv(
            bot_name=self.settings.bot_name,
            device_id=self.settings.device_id,
            channel_name=self.settings.resolved_pubsub_channel,
        )

        await self.emit(started_event)

        self.running = True

        while self.running:
            events = await self.subscriber.read()

            if not events:
                continue

            for payload in events:
                try:
                    message_event = self.build_message_event(payload)
                    await self.emit(message_event)

                except Exception as exc:
                    print(
                        {
                            "error": str(exc),
                            "channel": self.settings.resolved_pubsub_channel,
                            "payload": payload,
                        }
                    )

    async def stop(self) -> None:
        if self._stopping:
            return

        self._stopping = True
        self.running = False

        try:
            await self.subscriber.close()
        finally:
            await self._whatsapp.close()

    async def _main(self) -> None:
        try:
            await self.start()
        finally:
            await self.stop()

    def run(self) -> None:
        try:
            asyncio.run(self._main())
        except KeyboardInterrupt:
            print("Worker stopped by user")
