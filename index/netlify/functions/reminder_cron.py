import json
from datetime import datetime, timedelta
import asyncio
from telegram import Bot

TOKEN = "8593589562:AAEzpabdygda057aFSyDrUq3mIwkWoKsKVY"
DATA_FILE = "/tmp/events.json"

async def send_reminders():
    bot = Bot(TOKEN)
    now = datetime.utcnow()
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return
    
    for e in data["events"]:
        event_time = datetime.fromisoformat(e["event_time"])
        for m in e["notify_minutes"]:
            notify_time = event_time - timedelta(minutes=m)
            if abs((notify_time - now).total_seconds()) < 150:
                await bot.send_message(
                    e["chat_id"],
                    f"⏰ Напоминание:\n{e['title']}\nчерез {m} мин."
                )

def handler(event, context):
    asyncio.run(send_reminders())
    return {"statusCode": 200}
