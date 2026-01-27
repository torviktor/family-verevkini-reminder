import json
from datetime import datetime, timedelta
from telegram import Bot

TOKEN = "ВСТАВЬ_СЮДА_TOKEN_ОТ_BOTFATHER"
DATA_FILE = "data/events.json"


def handler(event, context):
    bot = Bot(TOKEN)
    now = datetime.utcnow()

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for e in data["events"]:
        event_time = datetime.fromisoformat(e["event_time"])

        for m in e["notify_minutes"]:
            notify_time = event_time - timedelta(minutes=m)

            if abs((notify_time - now).total_seconds()) < 150:
                bot.send_message(
                    e["chat_id"],
                    f"⏰ Напоминание:\n{e['title']}\nчерез {m} мин."
                )

    return {"statusCode": 200}
