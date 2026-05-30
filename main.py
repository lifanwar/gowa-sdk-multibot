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

    # Handling Group
    if message.is_group:
        return

    # Handling outgoing message
    if message.direction == "outgoing":
        if text == "done":
            await client.reply_message("yes", message)

    # Handling incoming
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
