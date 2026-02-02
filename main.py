import json
import uuid
import os
from datetime import datetime, timedelta
import asyncio
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          MessageHandler, ContextTypes, filters)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATA_FILE = "events.json"

# Часовой пояс Москва
TIMEZONE = pytz.timezone("Europe/Moscow")


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


# ============= ГЛАВНОЕ МЕНЮ =============


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню бота"""
    context.user_data.clear()

    keyboard = [
        [
            InlineKeyboardButton("➕ Добавить событие",
                                 callback_data="add_event")
        ],
        [
            InlineKeyboardButton("📋 Список событий",
                                 callback_data="list_events")
        ],
        [
            InlineKeyboardButton("🗑️ Удалить событие",
                                 callback_data="delete_event")
        ],
        [InlineKeyboardButton("❓ Справка", callback_data="help")],
    ]

    message_text = "🔔 *Бот напоминаний*\n\nВыберите действие:"

    if update.message:
        await update.message.reply_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown")
    elif update.callback_query:
        try:
            await update.callback_query.message.edit_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown")
        except:
            await update.callback_query.message.reply_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown")


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /menu для быстрого доступа"""
    await start(update, context)


# ============= СПРАВКА =============


async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать справку"""

    help_text = f"""❓ *СПРАВКА*

🔔 *Что умеет бот:*
- Создавать разовые и повторяющиеся события
- Отправлять напоминания в группу
- Управлять списком событий

📝 *Как создать событие:*
1️⃣ Нажмите "➕ Добавить событие"
2️⃣ Введите название события
3️⃣ Укажите дату и время
4️⃣ Выберите тип повторения
5️⃣ Настройте напоминания

🔄 *Типы повторений:*
🔴 Один раз — событие произойдёт только один раз
📆 Каждый день — ежедневное повторение
📅 Каждую неделю — еженедельное повторение
📊 Каждый месяц — ежемесячное повторение

⏰ *Напоминания:*
Вы можете выбрать одно или несколько напоминаний:
- За 1 час до события
- За 30 минут
- За 15 минут
- За 5 минут
- В момент события
- Или свой вариант (например: за 2 дня = 2880 минут)

🎮 *Команды бота:*
/menu — Главное меню бота
/cancel — Отменить текущее действие
/help — Показать справку
/debug — Отладочная информация

⚠️ *ВАЖНО - Часовой пояс:*
- Бот использует часовой пояс: *Europe/Moscow (GMT+3)*
- Указывайте время по *вашему местному времени*
- Пример: если у вас сейчас 15:00, пишите 15:00

📅 *Формат даты:*
`YYYY-MM-DD HH:MM` (год-месяц-день часы:минуты)

Примеры:
- `2026-02-15 18:00` — 15 февраля в 18:00
- `2026-03-01 09:30` — 1 марта в 9:30
- `2026-12-31 23:59` — 31 декабря в 23:59

❌ *Отмена действия:*
В любой момент можете:
- Написать команду /cancel
- Нажать кнопку "❌ Отменить"
"""

    keyboard = [[
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    ]]

    # Проверяем откуда пришёл запрос
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.message.edit_text(
                help_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown")
        except:
            await update.callback_query.message.reply_text(
                help_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown")
    else:
        await update.message.reply_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown")


# ============= ОТЛАДКА =============


async def debug_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать отладочную информацию"""
    now_utc = datetime.now(pytz.UTC)
    now_moscow = now_utc.astimezone(TIMEZONE)

    data = load_data()
    chat_events = [
        e for e in data["events"] if e["chat_id"] == update.effective_chat.id
    ]

    info = f"""🔧 *Отладочная информация*

📍 Chat ID: `{update.effective_chat.id}`
🕐 Время UTC: `{now_utc.strftime('%Y-%m-%d %H:%M:%S')}`
🕐 Время Москва: `{now_moscow.strftime('%Y-%m-%d %H:%M:%S')}`
📊 События в этом чате: {len(chat_events)}

"""

    if chat_events:
        info += "*События:*\n"
        for e in chat_events[:5]:  # Показать первые 5
            try:
                event_dt = datetime.fromisoformat(e["event_time"].replace(
                    '+00:00',
                    '')).replace(tzinfo=pytz.UTC).astimezone(TIMEZONE)
                info += f"• {e['title']} — {event_dt.strftime('%d.%m %H:%M')}\n"
            except:
                info += f"• {e['title']} — ошибка парсинга даты\n"

    await update.message.reply_text(info, parse_mode="Markdown")


# ============= ОТМЕНА =============


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменить текущее действие"""
    context.user_data.clear()

    keyboard = [[
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    ]]

    message_text = "❌ *Действие отменено*\n\nВсе несохранённые данные удалены."

    if update.message:
        await update.message.reply_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown")
    elif update.callback_query:
        try:
            await update.callback_query.message.edit_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown")
        except:
            await update.callback_query.message.reply_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown")


# ============= ДОБАВЛЕНИЕ СОБЫТИЯ =============


async def add_event_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления события"""
    query = update.callback_query
    await query.answer()

    context.user_data["step"] = "title"
    context.user_data["chat_id"] = update.effective_chat.id

    keyboard = [[InlineKeyboardButton("❌ Отменить", callback_data="cancel")]]

    await query.message.reply_text(
        "📝 *Шаг 1/4: Название события*\n\n"
        "Введите название события:\n\n"
        "_Например: День рождения, Встреча, Оплатить счета_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown")


async def add_event_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор даты события"""
    context.user_data["title"] = update.message.text
    context.user_data["step"] = "date"

    now_local = datetime.now(TIMEZONE)

    keyboard = [[InlineKeyboardButton("❌ Отменить", callback_data="cancel")]]

    await update.message.reply_text(
        "📅 *Шаг 2/4: Дата и время*\n\n"
        "Введите дату и время в формате:\n"
        "`YYYY-MM-DD HH:MM`\n\n"
        f"🕐 Сейчас у вас: `{now_local.strftime('%Y-%m-%d %H:%M')}`\n\n"
        "Примеры:\n"
        "• `2026-02-15 18:00` — 15 февраля в 18:00\n"
        "• `2026-03-01 09:30` — 1 марта в 9:30",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown")


async def add_event_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор типа повторения"""
    try:
        dt_naive = datetime.strptime(update.message.text.strip(),
                                     "%Y-%m-%d %H:%M")
        dt_local = TIMEZONE.localize(dt_naive)
        dt_utc = dt_local.astimezone(pytz.UTC)

        context.user_data["event_time"] = dt_utc.isoformat()
        context.user_data["step"] = "repeat"

        keyboard = [
            [InlineKeyboardButton("🔴 Один раз", callback_data="repeat_once")],
            [
                InlineKeyboardButton("📆 Каждый день",
                                     callback_data="repeat_daily")
            ],
            [
                InlineKeyboardButton("📅 Каждую неделю",
                                     callback_data="repeat_weekly")
            ],
            [
                InlineKeyboardButton("📊 Каждый месяц",
                                     callback_data="repeat_monthly")
            ],
            [InlineKeyboardButton("❌ Отменить", callback_data="cancel")],
        ]

        await update.message.reply_text(
            "🔄 *Шаг 3/4: Повторение*\n\n"
            "Как часто повторять событие?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown")
    except ValueError:
        keyboard = [[
            InlineKeyboardButton("❌ Отменить", callback_data="cancel")
        ]]
        await update.message.reply_text(
            "❌ *Неверный формат даты!*\n\n"
            "Используйте формат: `YYYY-MM-DD HH:MM`\n\n"
            "Примеры правильного формата:\n"
            "✅ `2026-02-15 18:00`\n"
            "✅ `2026-12-31 23:59`\n\n"
            "Попробуйте ещё раз:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown")


async def add_event_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор времени напоминаний"""
    query = update.callback_query
    await query.answer()

    repeat_map = {
        "repeat_once": "once",
        "repeat_daily": "daily",
        "repeat_weekly": "weekly",
        "repeat_monthly": "monthly"
    }

    context.user_data["repeat"] = repeat_map.get(query.data, "once")
    context.user_data["step"] = "notify"

    keyboard = [
        [InlineKeyboardButton("🔔 За 1 час", callback_data="notify_60")],
        [InlineKeyboardButton("🔔 За 30 минут", callback_data="notify_30")],
        [InlineKeyboardButton("🔔 За 15 минут", callback_data="notify_15")],
        [InlineKeyboardButton("🔔 За 5 минут", callback_data="notify_5")],
        [InlineKeyboardButton("⏰ В момент события", callback_data="notify_0")],
        [
            InlineKeyboardButton("✏️ Выбрать несколько",
                                 callback_data="notify_custom")
        ],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel")],
    ]

    await query.message.reply_text(
        "⏰ *Шаг 4/4: Напоминания*\n\n"
        "Когда напомнить о событии?\n\n"
        "_Можете выбрать один вариант или указать несколько_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown")


async def add_event_custom_notify(update: Update,
                                  context: ContextTypes.DEFAULT_TYPE):
    """Запрос нескольких напоминаний"""
    query = update.callback_query
    await query.answer()

    context.user_data["step"] = "notify_custom"

    keyboard = [[InlineKeyboardButton("❌ Отменить", callback_data="cancel")]]

    await query.message.reply_text(
        "⏰ *Настройка напоминаний*\n\n"
        "Введите время напоминаний в *минутах* через запятую.\n\n"
        "📌 Примеры:\n"
        "• `60,30,15,0` — за час, полчаса, 15 мин и в момент\n"
        "• `1440,60` — за сутки и за час\n"
        "• `2880,1440` — за 2 дня и за сутки\n"
        "• `0` — только в момент события\n\n"
        "💡 1 час = 60 мин, 1 день = 1440 мин",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown")


async def save_event(update: Update, context: ContextTypes.DEFAULT_TYPE,
                     notify_minutes):
    """Сохранение события"""
    data = load_data()

    event = {
        "id": str(uuid.uuid4()),
        "chat_id": context.user_data["chat_id"],
        "title": context.user_data["title"],
        "event_time": context.user_data["event_time"],
        "repeat": context.user_data.get("repeat", "once"),
        "notify_minutes": notify_minutes,
        "created_by": update.effective_user.id,
        "created_at": datetime.utcnow().isoformat(),
        "sent_notifications": []
    }

    data["events"].append(event)
    save_data(data)

    repeat_text = {
        "once": "Один раз",
        "daily": "Каждый день",
        "weekly": "Каждую неделю",
        "monthly": "Каждый месяц"
    }

    notify_text = []
    for m in sorted(notify_minutes, reverse=True):
        if m == 0:
            notify_text.append("в момент события")
        elif m < 60:
            notify_text.append(f"за {m} мин")
        elif m < 1440:
            hours = m // 60
            notify_text.append(f"за {hours} ч")
        else:
            days = m // 1440
            notify_text.append(f"за {days} д")

    event_dt_utc = datetime.fromisoformat(event["event_time"])
    event_dt_local = event_dt_utc.astimezone(TIMEZONE)

    success_message = (
        "✅ *Событие создано!*\n\n"
        f"📝 {event['title']}\n"
        f"📅 {event_dt_local.strftime('%d.%m.%Y в %H:%M')} (МСК)\n"
        f"🔄 {repeat_text[event['repeat']]}\n"
        f"🔔 Напоминания: {', '.join(notify_text)}")

    context.user_data.clear()

    keyboard = [[
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    ]]

    if update.message:
        await update.message.reply_text(
            success_message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown")
    else:
        await update.callback_query.message.reply_text(
            success_message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown")


# ============= СПИСОК СОБЫТИЙ =============


async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список событий"""
    query = update.callback_query
    await query.answer()

    data = load_data()
    chat_events = [
        e for e in data["events"] if e["chat_id"] == update.effective_chat.id
    ]

    if not chat_events:
        try:
            await query.message.edit_text(
                "📋 *Список событий*\n\n"
                "Событий пока нет.\n"
                "Создайте первое событие!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Главное меню",
                                         callback_data="main_menu")
                ]]),
                parse_mode="Markdown")
        except:
            await query.message.reply_text(
                "📋 *Список событий*\n\n"
                "Событий пока нет.\n"
                "Создайте первое событие!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Главное меню",
                                         callback_data="main_menu")
                ]]),
                parse_mode="Markdown")
        return

    chat_events.sort(key=lambda e: datetime.fromisoformat(e[
        "event_time"].replace('+00:00', '')))

    repeat_emoji = {"once": "🔴", "daily": "📆", "weekly": "📅", "monthly": "📊"}

    message = "📋 *Список событий*\n\n"

    for i, event in enumerate(chat_events, 1):
        try:
            event_dt_utc = datetime.fromisoformat(event["event_time"].replace(
                '+00:00', '')).replace(tzinfo=pytz.UTC)
            event_dt_local = event_dt_utc.astimezone(TIMEZONE)
            emoji = repeat_emoji.get(event.get("repeat", "once"), "🔴")
            message += f"{i}. {emoji} *{event['title']}*\n"
            message += f"   📅 {event_dt_local.strftime('%d.%m.%Y в %H:%M')}\n\n"
        except Exception as e:
            message += f"{i}. ❓ *{event['title']}* (ошибка даты)\n\n"

    keyboard = [[
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    ]]

    try:
        await query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown")
    except:
        await query.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown")


# ============= УДАЛЕНИЕ СОБЫТИЯ =============


async def delete_event_list(update: Update,
                            context: ContextTypes.DEFAULT_TYPE):
    """Показать список для удаления"""
    query = update.callback_query
    await query.answer()

    data = load_data()
    chat_events = [
        e for e in data["events"] if e["chat_id"] == update.effective_chat.id
    ]

    if not chat_events:
        try:
            await query.message.edit_text(
                "🗑️ *Удаление событий*\n\n"
                "Нет событий для удаления.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Главное меню",
                                         callback_data="main_menu")
                ]]),
                parse_mode="Markdown")
        except:
            await query.message.reply_text(
                "🗑️ *Удаление событий*\n\n"
                "Нет событий для удаления.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Главное меню",
                                         callback_data="main_menu")
                ]]),
                parse_mode="Markdown")
        return

    keyboard = []
    for event in chat_events:
        try:
            event_dt_utc = datetime.fromisoformat(event["event_time"].replace(
                '+00:00', '')).replace(tzinfo=pytz.UTC)
            event_dt_local = event_dt_utc.astimezone(TIMEZONE)
            button_text = f"🗑️ {event['title']} ({event_dt_local.strftime('%d.%m')})"
        except:
            button_text = f"🗑️ {event['title']}"
        keyboard.append([
            InlineKeyboardButton(button_text,
                                 callback_data=f"del_{event['id']}")
        ])

    keyboard.append(
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])

    try:
        await query.message.edit_text(
            "🗑️ *Удаление событий*\n\n"
            "Выберите событие для удаления:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown")
    except:
        await query.message.reply_text(
            "🗑️ *Удаление событий*\n\n"
            "Выберите событие для удаления:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown")


async def delete_event_confirm(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    """Удалить событие"""
    query = update.callback_query
    await query.answer()

    event_id = query.data.replace("del_", "")

    data = load_data()
    event = next((e for e in data["events"] if e["id"] == event_id), None)

    if event:
        data["events"] = [e for e in data["events"] if e["id"] != event_id]
        save_data(data)

        try:
            await query.message.edit_text(
                f"✅ Событие *{event['title']}* удалено!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Главное меню",
                                         callback_data="main_menu")
                ]]),
                parse_mode="Markdown")
        except:
            await query.message.reply_text(
                f"✅ Событие *{event['title']}* удалено!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Главное меню",
                                         callback_data="main_menu")
                ]]),
                parse_mode="Markdown")
    else:
        try:
            await query.message.edit_text("❌ Событие не найдено.",
                                          reply_markup=InlineKeyboardMarkup([[
                                              InlineKeyboardButton(
                                                  "🏠 Главное меню",
                                                  callback_data="main_menu")
                                          ]]),
                                          parse_mode="Markdown")
        except:
            await query.message.reply_text("❌ Событие не найдено.",
                                           reply_markup=InlineKeyboardMarkup([[
                                               InlineKeyboardButton(
                                                   "🏠 Главное меню",
                                                   callback_data="main_menu")
                                           ]]),
                                           parse_mode="Markdown")


# ============= ОБРАБОТЧИКИ =============


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок"""
    query = update.callback_query

    try:
        if query.data == "main_menu":
            await start(update, context)
        elif query.data == "help":
            await help_menu(update, context)
        elif query.data == "cancel":
            await cancel(update, context)
        elif query.data == "add_event":
            await add_event_start(update, context)
        elif query.data == "list_events":
            await list_events(update, context)
        elif query.data == "delete_event":
            await delete_event_list(update, context)
        elif query.data.startswith("repeat_"):
            await add_event_notify(update, context)
        elif query.data == "notify_custom":
            await add_event_custom_notify(update, context)
        elif query.data.startswith("notify_"):
            minutes = int(query.data.replace("notify_", ""))
            await save_event(update, context, [minutes])
        elif query.data.startswith("del_"):
            await delete_event_confirm(update, context)
    except Exception as e:
        print(f"❌ Error in button_handler: {e}")
        await query.answer("Произошла ошибка. Попробуйте ещё раз.")


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    step = context.user_data.get("step")

    try:
        if step == "title":
            await add_event_date(update, context)
        elif step == "date":
            await add_event_repeat(update, context)
        elif step == "notify_custom":
            try:
                notify_minutes = [
                    int(x.strip()) for x in update.message.text.split(",")
                ]
                await save_event(update, context, notify_minutes)
            except ValueError:
                keyboard = [[
                    InlineKeyboardButton("❌ Отменить", callback_data="cancel")
                ]]
                await update.message.reply_text(
                    "❌ *Неверный формат!*\n\n"
                    "Введите числа через запятую.\n\n"
                    "Примеры:\n"
                    "✅ `60,30,15,0`\n"
                    "✅ `1440,60`\n"
                    "✅ `0`\n\n"
                    "Попробуйте ещё раз:",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Error in text_handler: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка. Попробуйте ещё раз или напишите /cancel")


# ============= НАПОМИНАНИЯ =============


def get_next_occurrence(event_time, repeat_type):
    """Получить следующее время события с учётом повторения"""
    now = datetime.now(pytz.UTC)

    try:
        if isinstance(event_time, str):
            event_time_clean = event_time.replace('+00:00', '')
            event_dt = datetime.fromisoformat(event_time_clean)
        else:
            event_dt = event_time

        if event_dt.tzinfo is None:
            event_dt = pytz.UTC.localize(event_dt)
    except Exception as e:
        print(f"❌ Error parsing event_time: {event_time}, error: {e}")
        return None

    if not repeat_type or repeat_type == "once":
        return event_dt if event_dt > now else None

    next_dt = event_dt

    max_iterations = 365  # Защита от бесконечного цикла
    iterations = 0

    while next_dt <= now and iterations < max_iterations:
        if repeat_type == "daily":
            next_dt += timedelta(days=1)
        elif repeat_type == "weekly":
            next_dt += timedelta(weeks=1)
        elif repeat_type == "monthly":
            next_dt += timedelta(days=30)
        else:
            break
        iterations += 1

    return next_dt if next_dt > now else None


async def check_reminders(application):
    """Проверка и отправка напоминаний"""
    bot = application.bot
    print("🔔 Reminder checker started!")

    while True:
        try:
            now = datetime.now(pytz.UTC)
            data = load_data()

            now_moscow = now.astimezone(TIMEZONE)
            print(
                f"⏰ Checking reminders at {now_moscow.strftime('%Y-%m-%d %H:%M:%S')} MSK"
            )

            for event in data.get("events", []):
                try:
                    if "event_time" not in event or "notify_minutes" not in event:
                        continue

                    repeat_type = event.get("repeat", "once")
                    next_occurrence = get_next_occurrence(
                        event["event_time"], repeat_type)

                    if not next_occurrence:
                        continue

                    if "sent_notifications" not in event:
                        event["sent_notifications"] = []

                    for minutes in event["notify_minutes"]:
                        notify_time = next_occurrence - timedelta(
                            minutes=minutes)
                        time_diff = (notify_time - now).total_seconds()

                        notification_key = f"{next_occurrence.isoformat()}_{minutes}"

                        if -45 < time_diff < 45 and notification_key not in event[
                                "sent_notifications"]:
                            try:
                                event_local = next_occurrence.astimezone(
                                    TIMEZONE)

                                if minutes == 0:
                                    message = f"⏰ *Событие началось!*\n\n📝 {event['title']}\n🕐 {event_local.strftime('%H:%M')}"
                                elif minutes < 60:
                                    message = f"⏰ *Напоминание*\n\n📝 {event['title']}\n⏱ Через {minutes} мин\n🕐 Событие в {event_local.strftime('%H:%M')}"
                                elif minutes < 1440:
                                    hours = minutes // 60
                                    message = f"⏰ *Напоминание*\n\n📝 {event['title']}\n⏱ Через {hours} ч\n🕐 Событие в {event_local.strftime('%H:%M')}"
                                else:
                                    days = minutes // 1440
                                    message = f"⏰ *Напоминание*\n\n📝 {event['title']}\n⏱ Через {days} д\n📅 Событие {event_local.strftime('%d.%m в %H:%M')}"

                                await bot.send_message(event["chat_id"],
                                                       message,
                                                       parse_mode="Markdown")

                                event["sent_notifications"].append(
                                    notification_key)
                                save_data(data)

                                print(
                                    f"✅ Sent reminder for '{event['title']}' ({minutes} min) to chat {event['chat_id']}"
                                )
                            except Exception as ex:
                                print(f"❌ Error sending reminder: {ex}")

                    if event.get("sent_notifications"):
                        cutoff = (now - timedelta(days=2)).isoformat()
                        event["sent_notifications"] = [
                            n for n in event["sent_notifications"]
                            if n.split("_")[0] > cutoff
                        ]

                except Exception as e:
                    print(
                        f"❌ Error processing event '{event.get('title', 'Unknown')}': {e}"
                    )
                    continue

            await asyncio.sleep(30)
        except Exception as e:
            print(f"❌ Error in check_reminders: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(30)


# ============= KEEP ALIVE (против засыпания) =============


async def keep_alive(application):
    """Периодический пинг чтобы Replit не засыпал"""
    print("💚 Keep-alive started!")

    while True:
        try:
            await asyncio.sleep(1800)  # Каждые 30 минут

            # Просто проверяем что бот жив
            me = await application.bot.get_me()
            print(f"💚 Keep-alive ping: Bot @{me.username} is alive!")

        except Exception as e:
            print(f"❌ Keep-alive error: {e}")
            await asyncio.sleep(1800)


# ============= ОБРАБОТКА ОШИБОК =============


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальная обработка ошибок"""
    print(f"❌ Error: {context.error}")
    import traceback
    traceback.print_exc()

    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка. Попробуйте ещё раз или напишите /menu")
    except:
        pass


# ============= ИНИЦИАЛИЗАЦИЯ =============


async def post_init(application):
    """Запуск фоновых задач и установка команд"""
    commands = [
        BotCommand("menu", "Главное меню бота"),
        BotCommand("cancel", "Отменить текущее действие"),
        BotCommand("help", "Справка по использованию"),
        BotCommand("debug", "Отладочная информация"),
    ]
    await application.bot.set_my_commands(commands)

    # Запуск фоновых задач
    asyncio.create_task(check_reminders(application))
    asyncio.create_task(keep_alive(application))

    print("✅ Bot initialization complete!")


# ============= ЗАПУСК =============


def main():
    application = Application.builder().token(TOKEN).post_init(
        post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("help", help_menu))
    application.add_handler(CommandHandler("debug", debug_info))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # Глобальный обработчик ошибок
    application.add_error_handler(error_handler)

    print("🤖 Bot started!")
    print(f"🕐 Timezone: {TIMEZONE}")
    print("=" * 50)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
