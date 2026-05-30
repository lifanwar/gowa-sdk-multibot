# Automation Core

`automation_core` adalah framework sederhana untuk membuat worker bot WhatsApp berbasis GOWA Multi-Device. Worker membaca event dari Redis Pub/Sub, mengubah payload menjadi event Python, lalu menjalankan handler yang didaftarkan dengan `@bot.event(...)`.

## Struktur Utama

```text
automation_core/
├── __init__.py
├── client.py
├── events.py
├── message.py
├── redis_pubsub.py
├── settings.py
└── gowa_api.py
```

Penjelasan singkat:

* `client.py` berisi `AutomationClient`, event handler, lifecycle worker, dan helper berbasis `IncomingMessage`.
* `gowa_api.py` berisi HTTP request ke GOWA API.
* `redis_pubsub.py` membaca event dari Redis Pub/Sub.
* `message.py` berisi model pesan.
* `events.py` berisi event seperti `StartedEv` dan `MessageEv`.
* `settings.py` membaca konfigurasi dari `.env`.

## Instalasi

```bash
pip install httpx redis pydantic-settings
```

Jika package dipakai secara lokal:

```bash
pip install -e .
```

## Contoh `.env`

```env
BOT_NAME=automation-bot
DEVICE_ID=device-001

REDIS_URL=redis://localhost:6379/0
PUBSUB_CHANNEL_PREFIX=wa:incoming
PUBSUB_POLL_TIMEOUT_SECONDS=1
REDIS_RECONNECT_SLEEP_SECONDS=2

GOWA_BASE_URL=http://localhost:3000
GOWA_DEVICE_ID=device-001
GOWA_SEND_MESSAGE_PATH=/send/message

GOWA_BASIC_AUTH_USERNAME=
GOWA_BASIC_AUTH_PASSWORD=
```

Jika `GOWA_DEVICE_ID` kosong, sistem akan memakai `DEVICE_ID`.

## Contoh Penggunaan

```python
from automation_core import AutomationClient, MessageEv, StartedEv

bot = AutomationClient()


@bot.event(StartedEv)
async def on_started(client: AutomationClient, event: StartedEv):
    print(
        {
            "status": "started",
            "bot_name": event.bot_name,
            "device_id": event.device_id,
            "channel": event.channel_name,
        }
    )


@bot.event(MessageEv)
async def on_message(client: AutomationClient, event: MessageEv):
    message = event.message
    text = message.text.lower().strip()

    print(
        {
            "event": event.event_name,
            "device_id": event.device_id,
            "message_id": message.id,
            "chat_id": message.chat_id,
            "sender": message.sender,
            "direction": message.direction,
            "text": message.text,
            "has_media": message.has_media,
        }
    )

    if message.is_group:
        return

    if message.direction == "outgoing":
        if text == "done":
            await client.reply_message("yes", message)

    if message.direction == "incoming":
        if text == "ping":
            await client.send_message("pong", message)
            return

        if text == "test":
            msg = await client.reply_message("processing...", message)

            await client.update_message("pong", msg, message)
            return


if __name__ == "__main__":
    bot.run()
```

## Public Import

Agar import berikut bisa digunakan:

```python
from automation_core import AutomationClient, MessageEv, StartedEv
```

isi `automation_core/__init__.py`:

```python
from automation_core.client import AutomationClient
from automation_core.events import MessageEv, StartedEv
from automation_core.message import IncomingMessage

__all__ = [
    "AutomationClient",
    "MessageEv",
    "StartedEv",
    "IncomingMessage",
]
```

## Method Utama

### `client.send_message(text, message)`

Mengirim pesan biasa ke chat yang sama dengan `IncomingMessage`.

```python
await client.send_message("pong", message)
```

### `client.reply_message(text, message)`

Mengirim pesan sebagai reply/quote ke pesan sebelumnya.

```python
await client.reply_message("yes", message)
```

### `client.update_message(text, target_message, message)`

Mengedit pesan bot yang sebelumnya sudah dikirim.

```python
msg = await client.reply_message("processing...", message)

await client.update_message("pong", msg, message)
```

`target_message` bisa berupa hasil return dari `send_message()` / `reply_message()`, atau langsung berupa `message_id`.

Contoh:

```python
await client.update_message("pong", msg, message)
```

atau:

```python
await client.update_message("pong", msg["message_id"], message)
```

## Alur Kerja

```text
GOWA Webhook
↓
Redis Pub/Sub
↓
AutomationClient
↓
MessageEv / StartedEv
↓
Handler user
↓
GoWaApi
↓
GOWA API
```

## IncomingMessage

Object `message` sudah dinormalisasi dari payload webhook.

Field utama:

```python
message.id
message.text
message.sender
message.chat_id
message.device_id
message.is_group
message.raw
```

Property helper:

```python
message.direction
message.contact_id
message.media_type
message.media_path
message.has_media
```

Contoh:

```python
if message.direction == "incoming":
    print(message.text)

if message.has_media:
    print(message.media_path)
```

## Tips

Gunakan `incoming` untuk memproses pesan dari user:

```python
if message.direction == "incoming":
    ...
```

Gunakan `outgoing` hanya jika memang ingin menangani pesan yang dikirim dari device sendiri.

Hindari membalas semua pesan `outgoing` tanpa filter, karena bisa menyebabkan loop.

## Catatan Desain

Framework ini memakai lapisan sederhana:

```text
Handler
↓
AutomationClient
↓
GoWaApi
↓
GOWA API
```

Endpoint HTTP mentah ditaruh di `gowa_api.py`.

Helper yang butuh konteks `IncomingMessage`, seperti `send_message(text, message)`, `reply_message(text, message)`, dan `update_message(text, target_message, message)`, ditaruh di `client.py`.

Struktur ini dibuat supaya handler tetap ringkas dan mudah digunakan.
