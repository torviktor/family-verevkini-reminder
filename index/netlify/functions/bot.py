import json
import uuid
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = "8593589562:AAEzpabdygda057aFSyDrUq3mIwkWoKsKVY"
DATA_FILE = "data/events.json"


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


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
        dt = datetime.strptime(update.message.text, "%Y-%m-%d %H:%M")
        context.user_data["event_time"] = dt.isoformat()
        context.user_data["step"] = "notify"
        await update.message.reply_text(
            "Когда напомнить? (в минутах, через запятую)\nНапример: 60,15,0"
        )

    elif step == "notify":
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


def handler(event, context):
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    update = Update.de_json(json.loads(event["body"]), app.bot)
    return app.process_update(update)

