from dotenv import load_dotenv
from pathlib import Path

from automation_core.client import AutomationClient
from automation_core.events import MessageEv, StartedEv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)


client = AutomationClient()


@client.event(StartedEv)
def on_started(client: AutomationClient, event: StartedEv):
    print(
        {
            "status": "started",
            "bot_name": event.bot_name,
            "device_id": event.device_id,
            "stream_name": event.stream_name,
        }
    )


@client.event(MessageEv)
async def on_message(client: AutomationClient, event: MessageEv):
    message = event.message

    if message.is_group:
        return

    if message.is_from_me:
        return

    text = message.text.lower().strip()

    if not text:
        return

    if text == "hi":
        print("sudah berhasil")
        await client.reply_message(
            "Halo, ini Sales Bot. Ada yang bisa dibantu?",
            message,
        )
        return

    if "harga" in text or "price" in text or "pricelist" in text:
        await client.reply_message(
            "Berikut daftar harga produk kami. Silakan sebutkan produk yang ingin dicek.",
            message,
        )
        return

    if "katalog" in text:
        await client.reply_message(
            "Berikut katalog produk kami: https://example.com/katalog",
            message,
        )
        return

    if "komplain" in text:
        await client.reply_message(
            "Baik, laporan Anda kami teruskan ke admin sales.",
            message,
        )

        await client.send_message(
            to="628xxxxxxxxxx",
            text=f"Komplain baru dari {message.sender}: {message.text}",
        )
        return

    await client.reply_message(
        "Halo, pesan Anda sudah kami terima. Tim sales akan membantu.",
        message,
    )


client.run()