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

    # Contoh: hanya balas pesan masuk, bukan pesan keluar dari device sendiri.
    if message.direction == "incoming" and message.text.lower().strip() == "ping":
        await client.reply_message("pong", message)


if __name__ == "__main__":
    bot.run()
