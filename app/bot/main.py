import json

import requests
import telebot
from telebot import types

from app.config import settings

bot = telebot.TeleBot(settings.telegram_bot_token, parse_mode="HTML")
user_tokens: dict[int, str] = {}


def get_api_token(telegram_user_id: int) -> str:
    if telegram_user_id not in user_tokens:
        response = requests.post(f"{settings.api_base_url}/auth/telegram/{telegram_user_id}", headers={"X-Bot-Auth-Secret": settings.bot_auth_secret}, timeout=10)
        response.raise_for_status()
        user_tokens[telegram_user_id] = response.json()["access_token"]
    return user_tokens[telegram_user_id]


def call_api(telegram_user_id: int, method: str, path: str, **kwargs):
    token = get_api_token(telegram_user_id)
    response = requests.request(method, f"{settings.api_base_url}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=10, **kwargs)
    if response.status_code == 401:
        user_tokens.pop(telegram_user_id, None)
        token = get_api_token(telegram_user_id)
        response = requests.request(method, f"{settings.api_base_url}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=10, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else None


def create_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("📋 Посмотреть список")
    keyboard.row("📋 Мои привычки", "➕ Добавить привычку")
    keyboard.row("⏰ Время напоминания", "ℹ️ Помощь")
    return keyboard


@bot.message_handler(commands=["start", "help"])
def show_welcome(message):
    text = ("Привет! Я помогу отслеживать ежедневные привычки.\n\n"
            "Выберите действие в меню: просмотреть список, добавить привычку, "
            "отметить выполнение или настроить напоминание.")
    bot.send_message(message.chat.id, text, reply_markup=create_main_keyboard())


@bot.message_handler(func=lambda message: message.text in ("📋 Мои привычки", "📋 Посмотреть список"))
def show_habits(message):
    try:
        habits = call_api(message.from_user.id, "GET", "/habits")
        if not habits:
            bot.send_message(message.chat.id, "Пока привычек нет. Нажмите «➕ Добавить привычку».", reply_markup=create_main_keyboard())
            return
        for habit in habits:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("✅ Выполнено", callback_data=f"done:{habit['id']}"),
                         types.InlineKeyboardButton("❌ Не выполнено", callback_data=f"missed:{habit['id']}"))
            keyboard.row(types.InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit:{habit['id']}"),
                         types.InlineKeyboardButton("🗑 Удалить", callback_data=f"delete:{habit['id']}"))
            description = habit["description"] or "Без описания"
            bot.send_message(message.chat.id,
                             f"<b>{habit['title']}</b>\n{description}\nПрогресс: {habit['successful_completions']}/{habit['target_completions']}",
                             reply_markup=keyboard)
    except Exception:
        bot.send_message(message.chat.id, "Не удалось получить привычки. Попробуйте позже.")


@bot.message_handler(func=lambda message: message.text == "➕ Добавить привычку")
def ask_habit_title(message):
    prompt = bot.send_message(message.chat.id, "Введите название новой привычки:")
    bot.register_next_step_handler(prompt, save_new_habit)


def save_new_habit(message):
    title = (message.text or "").strip()
    if not title:
        bot.send_message(message.chat.id, "Название не должно быть пустым. Попробуйте ещё раз.")
        return
    try:
        call_api(message.from_user.id, "POST", "/habits", json={"title": title, "description": "", "target_completions": 21})
        bot.send_message(message.chat.id, f"Привычка «{title}» добавлена.", reply_markup=create_main_keyboard())
    except Exception:
        bot.send_message(message.chat.id, "Не удалось сохранить привычку. Попробуйте позже.")


@bot.message_handler(func=lambda message: message.text == "⏰ Время напоминания")
def ask_reminder_time(message):
    prompt = bot.send_message(message.chat.id, "Введите время напоминания в формате ЧЧ:ММ, например 20:30.")
    bot.register_next_step_handler(prompt, save_reminder_time)


def save_reminder_time(message):
    try:
        hour_text, minute_text = (message.text or "").strip().split(":", maxsplit=1)
        hour, minute = int(hour_text), int(minute_text)
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError
        call_api(message.from_user.id, "PUT", "/settings/reminder", json={"hour": hour, "minute": minute})
        bot.send_message(message.chat.id, f"Напоминание установлено на {hour:02d}:{minute:02d}.", reply_markup=create_main_keyboard())
    except (ValueError, TypeError):
        bot.send_message(message.chat.id, "Неверный формат. Используйте ЧЧ:ММ, например 08:15.")
    except Exception:
        bot.send_message(message.chat.id, "Не удалось сохранить время напоминания.")


@bot.callback_query_handler(func=lambda callback: True)
def handle_habit_action(callback):
    try:
        action, habit_id_text = callback.data.split(":", maxsplit=1)
        habit_id = int(habit_id_text)
        telegram_user_id = callback.from_user.id
        if action in {"done", "missed"}:
            completed = action == "done"
            call_api(telegram_user_id, "PUT", f"/habits/{habit_id}/completion", params={"completed": str(completed).lower()})
            bot.answer_callback_query(callback.id, "Отметка сохранена")
            bot.send_message(callback.message.chat.id, "Выполнение отмечено." if completed else "Отмечено как невыполненное.")
        elif action == "delete":
            call_api(telegram_user_id, "DELETE", f"/habits/{habit_id}")
            bot.answer_callback_query(callback.id, "Привычка удалена")
            bot.edit_message_text("Привычка удалена.", callback.message.chat.id, callback.message.message_id)
        elif action == "edit":
            prompt = bot.send_message(callback.message.chat.id, "Введите новое название привычки:")
            bot.register_next_step_handler(prompt, save_habit_title, habit_id)
            bot.answer_callback_query(callback.id)
    except Exception:
        bot.answer_callback_query(callback.id, "Не удалось выполнить действие", show_alert=True)


def save_habit_title(message, habit_id: int):
    new_title = (message.text or "").strip()
    if not new_title:
        bot.send_message(message.chat.id, "Название не должно быть пустым.")
        return
    try:
        call_api(message.from_user.id, "PATCH", f"/habits/{habit_id}", json={"title": new_title})
        bot.send_message(message.chat.id, "Название привычки обновлено.", reply_markup=create_main_keyboard())
    except Exception:
        bot.send_message(message.chat.id, "Не удалось обновить привычку.")


@bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
def show_help(message):
    bot.send_message(message.chat.id, "Используйте меню для управления привычками. В списке можно отметить выполнение, изменить название или удалить привычку.", reply_markup=create_main_keyboard())


if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
