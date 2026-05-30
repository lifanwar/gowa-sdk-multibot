# Automation Core

`automation_core` adalah framework kecil untuk membuat worker bot WhatsApp berbasis GOWA Multi-Device. Worker ini membaca event dari Redis Pub/Sub, mengubah payload webhook menjadi event Python, lalu menjalankan handler yang kamu daftarkan dengan decorator `@bot.event(...)`.

Desain framework dibuat sederhana:

- `client.py` menangani lifecycle worker, event system, dan helper yang membutuhkan konteks message.
- `whatsapp_api.py` menangani seluruh HTTP request ke API GOWA/WhatsApp.
- `redis_pubsub.py` menangani koneksi Redis Pub/Sub.
- `message.py` berisi model pesan masuk.
- `events.py` berisi model event seperti `StartedEv` dan `MessageEv`.
- `settings.py` membaca konfigurasi dari `.env`.

Tujuan desain ini adalah menjaga code tetap mudah dibaca, tetapi tetap siap ditambah endpoint baru tanpa perlu membuat banyak folder atau layer tambahan.

---

## Struktur Folder

```text
automation_core/
├── __init__.py
├── client.py
├── events.py
├── message.py
├── redis_pubsub.py
├── settings.py
└── whatsapp_api.py
```

Penjelasan singkat:

```text
client.py
```

Berisi `AutomationClient`, yaitu class utama yang dipakai user. File ini mengatur event handler, membaca event dari Redis, membuat `MessageEv`, menjalankan handler, dan menyediakan helper seperti `reply_message()`.

```text
whatsapp_api.py
```

Berisi `WhatsAppApi`, yaitu class khusus untuk komunikasi HTTP ke GOWA API. Semua endpoint seperti `send_message()`, `update_message()`, `revoke_message()`, `send_image()`, dan endpoint lain nantinya ditambahkan di sini.

```text
events.py
```

Berisi dataclass event:

- `StartedEv`
- `MessageEv`

```text
message.py
```

Berisi dataclass `IncomingMessage`, termasuk property helper seperti:

- `direction`
- `contact_id`
- `media_type`
- `media_path`
- `has_media`
- `original_webhook_payload`

```text
redis_pubsub.py
```

Berisi `RedisPubSubSubscriber`, yaitu pembaca event dari Redis Pub/Sub.

```text
settings.py
```

Berisi konfigurasi dari `.env`.

---

## Instalasi Dependency

Minimal dependency yang digunakan:

```bash
pip install httpx redis pydantic-settings
```

Jika project kamu memakai editable install, pastikan package `automation_core` sudah terbaca oleh Python.

Contoh:

```bash
pip install -e .
```

atau jika package ada dalam folder tertentu:

```bash
pip install -e ./automation-core
```

---

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

Catatan:

Jika `GOWA_DEVICE_ID` tidak diisi, system akan fallback ke `DEVICE_ID`.

```python
resolved_gowa_device_id = gowa_device_id or device_id
```

Jadi header `X-Device-Id` tetap memiliki nilai.

---

## Cara Pakai Dasar

Contoh file `main.py`:

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

    # Abaikan group
    if message.is_group:
        return

    # Handling outgoing message
    if message.direction == "outgoing":
        if text == "done":
            await client.reply_message("yes", message)

    # Handling incoming message
    if message.direction == "incoming":
        if text == "ping":
            await client.reply_message("pong", message)


if __name__ == "__main__":
    bot.run()
```

---

## Import Public API

Agar import seperti ini bisa digunakan:

```python
from automation_core import AutomationClient, MessageEv, StartedEv
```

isi `automation_core/__init__.py` sebaiknya seperti ini:

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

---

## Alur Kerja Framework

Alur utama worker:

```text
GOWA webhook diterima oleh service lain
↓
Payload webhook dipublish ke Redis Pub/Sub
↓
RedisPubSubSubscriber membaca payload dari channel
↓
AutomationClient.build_message_event() membuat IncomingMessage dan MessageEv
↓
AutomationClient.emit() menjalankan handler yang cocok
↓
Handler memanggil client.reply_message(), client.send_message(), atau client.update_message()
↓
WhatsAppApi mengirim HTTP request ke GOWA API
```

---

## Event yang Tersedia

### `StartedEv`

Dikirim sekali saat worker berhasil start dan subscribe ke Redis channel.

Field:

```python
@dataclass
class StartedEv:
    bot_name: str
    device_id: str
    channel_name: str
```

Contoh:

```python
@bot.event(StartedEv)
async def on_started(client: AutomationClient, event: StartedEv):
    print("Worker started")
```

---

### `MessageEv`

Dikirim setiap ada payload message dari Redis Pub/Sub.

Field:

```python
@dataclass
class MessageEv:
    device_id: str
    message: IncomingMessage
    raw: dict[str, Any]
    event_name: str
    channel_name: str
    event_id: str | None = None
```

Contoh:

```python
@bot.event(MessageEv)
async def on_message(client: AutomationClient, event: MessageEv):
    message = event.message
    print(message.text)
```

---

## IncomingMessage

`IncomingMessage` adalah object pesan yang sudah dinormalisasi dari payload webhook.

Field utama:

```python
id: str | None
text: str
sender: str | None
chat_id: str | None
device_id: str
is_group: bool
raw: dict[str, Any]
```

Property tambahan:

```python
message.direction
message.contact_id
message.replied_to_id
message.timestamp
message.media_type
message.media_path
message.image
message.has_media
message.original_webhook_payload
```

Contoh:

```python
message = event.message

if message.direction == "incoming":
    print("Pesan masuk:", message.text)

if message.has_media:
    print("Media path:", message.media_path)
```

---

## Method yang Sudah Tersedia

### `client.reply_message(text, message)`

Membalas pesan berdasarkan object `IncomingMessage`.

Contoh:

```python
await client.reply_message("pong", message)
```

Method ini tetap ditaruh di `AutomationClient` karena membutuhkan konteks `IncomingMessage`.

Secara internal, method ini mengambil target dari:

```python
message.contact_id
```

Lalu mengirim pesan dengan `reply_message_id`.

---

### `client.send_message(to, text, extra_payload=None)`

Mengirim pesan baru ke target tertentu.

Contoh:

```python
await client.send_message(
    to="6281234567890@s.whatsapp.net",
    text="Halo"
)
```

Endpoint yang digunakan:

```text
POST /send/message
```

Payload:

```json
{
  "phone": "6281234567890@s.whatsapp.net",
  "message": "Halo"
}
```

---

### `client.update_message(message_id, to, text)`

Mengedit pesan yang sebelumnya sudah dikirim.

Contoh:

```python
await client.update_message(
    message_id="MESSAGE_ID_BOT",
    to="6281234567890@s.whatsapp.net",
    text="Pesan sudah diedit"
)
```

Endpoint yang digunakan:

```text
POST /message/{message_id}/update
```

Payload:

```json
{
  "phone": "6281234567890@s.whatsapp.net",
  "message": "Pesan sudah diedit"
}
```

Catatan:

`message_id` yang dipakai adalah ID pesan yang ingin diedit. Biasanya ini adalah ID pesan yang sebelumnya dikirim oleh bot, bukan ID pesan user.

---

## Contoh Alur Reply lalu Edit Message

Contoh: saat user mengirim `ping`, bot membalas `processing...`, lalu pesan itu diedit menjadi `pong`.

```python
@bot.event(MessageEv)
async def on_message(client: AutomationClient, event: MessageEv):
    message = event.message
    text = message.text.lower().strip()

    if message.is_group:
        return

    if message.direction == "incoming" and text == "ping":
        sent = await client.reply_message("processing...", message)

        sent_message_id = (
            sent.get("message_id")
            or sent.get("id")
            or sent.get("data", {}).get("message_id")
            or sent.get("data", {}).get("id")
        )

        if sent_message_id and message.contact_id:
            await client.update_message(
                message_id=sent_message_id,
                to=message.contact_id,
                text="pong",
            )
```

Kenapa perlu mengambil `sent_message_id`?

Karena endpoint edit message membutuhkan ID dari pesan yang akan diedit.

---

## Kenapa `whatsapp_api.py` Tidak Dipecah Per Endpoint?

Untuk tahap sekarang, endpoint yang dipakai masih sedikit:

- send message
- update message

Maka satu file `whatsapp_api.py` lebih sederhana dan mudah dirawat.

Struktur ini sengaja tidak memakai:

```text
api/
gateway.py
send_actions.py
message_actions.py
```

karena akan membuat penambahan endpoint terasa terlalu berlapis.

Aturan saat ini:

```text
client.py        → worker, event, handler lifecycle, helper berbasis IncomingMessage
whatsapp_api.py  → semua HTTP request ke GOWA API
settings.py      → konfigurasi
redis_pubsub.py  → Redis Pub/Sub
message.py       → model pesan
events.py        → model event
```

Jika nanti `whatsapp_api.py` sudah terlalu panjang, baru file ini boleh dipecah.

Batas praktis:

```text
Jika whatsapp_api.py sudah lebih dari 300–400 baris,
atau endpoint sudah terlalu banyak,
baru pertimbangkan memecahnya menjadi folder.
```

---

# Cara Menambahkan Endpoint Baru

Prinsip paling sederhana:

```text
Kalau endpoint itu request HTTP ke GOWA, tambahkan method di whatsapp_api.py.
```

Tidak perlu mengubah `client.py`, kecuali endpoint tersebut butuh konteks khusus dari `IncomingMessage`.

`AutomationClient` sudah mendelegasikan method yang tidak ditemukan ke `WhatsAppApi`, sehingga method baru di `whatsapp_api.py` bisa langsung dipanggil dari `client`.

Contoh:

```python
await client.revoke_message(...)
```

bisa berjalan jika `revoke_message()` sudah ada di `WhatsAppApi`.

---

## Template Menambahkan Endpoint POST

Gunakan pola ini di `whatsapp_api.py`:

```python
async def nama_endpoint(
    self,
    arg1: str,
    arg2: str,
) -> dict[str, Any]:
    if not arg1:
        raise ValueError("arg1 is required")

    if not arg2:
        raise ValueError("arg2 is required")

    path = "/path/endpoint"

    payload = {
        "field_1": arg1,
        "field_2": arg2,
    }

    return await self._post(path, payload)
```

---

## Contoh Tambah Endpoint Revoke Message

Misalnya ada endpoint:

```text
POST /message/{message_id}/revoke
```

Payload:

```json
{
  "phone": "6281234567890@s.whatsapp.net"
}
```

Tambahkan method berikut di `whatsapp_api.py`:

```python
async def revoke_message(
    self,
    message_id: str,
    to: str,
) -> dict[str, Any]:
    if not message_id:
        raise ValueError("message_id is required")

    if not to:
        raise ValueError("to is required")

    safe_message_id = quote(message_id, safe="")
    path = f"/message/{safe_message_id}/revoke"

    payload = {
        "phone": to,
    }

    return await self._post(path, payload)
```

Setelah itu langsung bisa dipakai dari handler:

```python
await client.revoke_message(
    message_id="MESSAGE_ID",
    to=message.contact_id,
)
```

Tidak perlu menambahkan wrapper di `AutomationClient`.

---

## Contoh Tambah Endpoint React Message

Misalnya ada endpoint:

```text
POST /message/{message_id}/react
```

Payload:

```json
{
  "phone": "6281234567890@s.whatsapp.net",
  "emoji": "👍"
}
```

Tambahkan method berikut di `whatsapp_api.py`:

```python
async def react_message(
    self,
    message_id: str,
    to: str,
    emoji: str,
) -> dict[str, Any]:
    if not message_id:
        raise ValueError("message_id is required")

    if not to:
        raise ValueError("to is required")

    if not emoji:
        raise ValueError("emoji is required")

    safe_message_id = quote(message_id, safe="")
    path = f"/message/{safe_message_id}/react"

    payload = {
        "phone": to,
        "emoji": emoji,
    }

    return await self._post(path, payload)
```

Setelah itu langsung bisa dipakai:

```python
await client.react_message(
    message_id=message.id,
    to=message.contact_id,
    emoji="👍",
)
```

---

## Contoh Tambah Endpoint Send Image

Misalnya ada endpoint:

```text
POST /send/image
```

Payload kira-kira:

```json
{
  "phone": "6281234567890@s.whatsapp.net",
  "image": "/path/to/image.jpg",
  "caption": "Ini caption"
}
```

Tambahkan method berikut di `whatsapp_api.py`:

```python
async def send_image(
    self,
    to: str,
    image: str,
    caption: str | None = None,
    extra_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not to:
        raise ValueError("to is required")

    if not image:
        raise ValueError("image is required")

    payload: dict[str, Any] = {
        "phone": to,
        "image": image,
    }

    if caption:
        payload["caption"] = caption

    if extra_payload:
        payload.update(extra_payload)

    return await self._post("/send/image", payload)
```

Pemakaian:

```python
await client.send_image(
    to=message.contact_id,
    image="/tmp/photo.jpg",
    caption="Ini gambarnya",
)
```

---

## Kapan Harus Menambahkan Method di `client.py`?

Tambahkan method di `client.py` hanya jika method tersebut membutuhkan konteks internal worker atau object `IncomingMessage`.

Contoh yang memang cocok di `client.py`:

```python
reply_message(text, message)
```

Karena dia butuh:

```python
message.contact_id
message.id
```

dan fungsinya adalah helper berbasis message event.

Contoh yang tidak perlu ditaruh di `client.py`:

```python
send_message()
update_message()
revoke_message()
react_message()
send_image()
send_file()
```

Itu cukup di `whatsapp_api.py`, karena semuanya murni HTTP API call.

---

## Aturan Penamaan Method

Gunakan nama yang jelas dan konsisten:

```text
send_message      → kirim pesan teks baru
send_image        → kirim gambar baru
send_file         → kirim file baru
update_message    → edit pesan lama
revoke_message    → hapus/tarik pesan lama
react_message     → beri reaction ke pesan lama
```

Jangan gunakan nama yang terlalu pendek seperti:

```text
send()
update()
react()
```

karena nanti kurang jelas ketika dipakai dari handler.

Lebih baik:

```python
await client.send_message(...)
await client.update_message(...)
await client.react_message(...)
```

daripada:

```python
await client.send(...)
await client.update(...)
await client.react(...)
```

---

## Error Handling

Saat ini `whatsapp_api.py` menggunakan:

```python
response.raise_for_status()
```

Artinya jika GOWA API mengembalikan status `400`, `401`, `404`, atau `500`, maka `httpx` akan melempar error.

Contoh handling di handler:

```python
import httpx

@bot.event(MessageEv)
async def on_message(client: AutomationClient, event: MessageEv):
    try:
        await client.reply_message("pong", event.message)
    except httpx.HTTPStatusError as exc:
        print(
            {
                "error": "gowa_api_error",
                "status_code": exc.response.status_code,
                "response": exc.response.text,
            }
        )
```

Kalau nanti ingin error handling lebih rapi, bisa dibuat custom exception. Tapi untuk tahap sekarang, `raise_for_status()` sudah cukup sederhana dan jelas.

---

## Tips Agar Tidak Loop

Hati-hati saat menangani pesan `outgoing`.

Contoh:

```python
if message.direction == "outgoing":
    if text == "done":
        await client.reply_message("yes", message)
```

Ini aman selama trigger-nya spesifik. Namun jika semua outgoing dibalas tanpa filter, bot bisa membuat loop atau merespons pesan miliknya sendiri terus-menerus.

Lebih aman:

```python
if message.direction == "incoming":
    # proses pesan dari user
    ...
```

Gunakan outgoing hanya untuk kebutuhan khusus.

---

## Catatan Desain

Framework ini sengaja dibuat dengan lapisan minimal:

```text
Handler user
↓
AutomationClient
↓
WhatsAppApi
↓
GOWA API
```

Tidak ada gateway tambahan dan tidak ada folder endpoint per resource.

Keuntungan:

- lebih mudah dipahami
- endpoint baru cukup ditambah di satu file
- handler tetap bersih
- tidak ada `client.gowa...`
- cocok untuk project worker bot kecil sampai menengah

Jika di masa depan endpoint sudah sangat banyak, struktur bisa berkembang menjadi:

```text
automation_core/
└── whatsapp/
    ├── http.py
    ├── send.py
    ├── message.py
    ├── group.py
    └── device.py
```

Namun untuk sekarang, struktur satu file `whatsapp_api.py` lebih tepat.
