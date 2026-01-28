import json
import uuid
import os
from datetime import datetime, timedelta
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.environ.get("TELEGRAM_TOKEN", "8593589562:AAEzpabdygda057aFSyDrUq3mIwkWoKsKVY")
DATA_FILE = "events.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"events": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"events": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Добавить событие", callback_data="add")],
        [InlineKeyboardButton("📋 Список событий", callback_data="list")]
    ]
    await update.message.reply_text(
        "Выбери действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "add":
        context.user_data["step"] = "title"
        await query.message.reply_text("Введите название события:")
    elif query.data == "list":
        data = load_data()
        if not data["events"]:
            await query.message.reply_text("Событий пока нет.")
            return
        text = "📋 Список событий:\n"
        for e in data["events"]:
            text += f"\n• {e['title']} — {e['event_time']}"
        await query.message.reply_text(text)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step")
    
    if step == "title":
        context.user_data["title"] = update.message.text
        context.user_data["step"] = "time"
        await update.message.reply_text("Дата и время (YYYY-MM-DD HH:MM):")
    elif step == "time":
        try:
            dt = datetime.strptime(update.message.text, "%Y-%m-%d %H:%M")
            context.user_data["event_time"] = dt.isoformat()
            context.user_data["step"] = "notify"
            await update.message.reply_text(
                "Когда напомнить? (в минутах, через запятую)\nНапример: 60,15,0"
            )
        except ValueError:
            await update.message.reply_text("❌ Неверный формат. Попробуйте снова (YYYY-MM-DD HH:MM):")
    elif step == "notify":
        try:
            notify = list(map(int, update.message.text.split(",")))
            data = load_data()
            data["events"].append({
                "id": str(uuid.uuid4()),
                "chat_id": update.effective_chat.id,
                "title": context.user_data["title"],
                "event_time": context.user_data["event_time"],
                "notify_minutes": notify
            })
            save_data(data)
            context.user_data.clear()
            await update.message.reply_text("✅ Событие добавлено")
        except ValueError:
            await update.message.reply_text("❌ Неверный формат минут. Попробуйте снова:")

# Фоновая задача для напоминаний
async def check_reminders(application):
    bot = application.bot
    while True:
        try:
            now = datetime.utcnow()
            data = load_data()
            
            for e in data.get("events", []):
                event_time = datetime.fromisoformat(e["event_time"])
                for m in e["notify_minutes"]:
                    notify_time = event_time - timedelta(minutes=m)
                    if abs((notify_time - now).total_seconds()) < 150:
                        try:
                            await bot.send_message(
                                e["chat_id"],
                                f"⏰ Напоминание:\n{e['title']}\nчерез {m} мин."
                            )
                        except Exception as ex:
                            print(f"Error sending: {ex}")
            
            await asyncio.sleep(300)  # Проверка каждые 5 минут
        except Exception as e:
            print(f"Error in reminders: {e}")
            await asyncio.sleep(300)

async def post_init(application):
    """Запускает фоновую задачу после инициализации"""
    asyncio.create_task(check_reminders(application))

def main():
    application = Application.builder().token(TOKEN).post_init(post_init).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(buttons))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    print("Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
```
