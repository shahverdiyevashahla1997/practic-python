import logging
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

import telebot
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Habit, HabitCompletion, User


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Используем время Баку, не меняя часовой пояс контейнера.
BAKU_TZ = ZoneInfo("Asia/Baku")

bot = telebot.TeleBot(settings.telegram_bot_token)


def send_due_reminders(
    database_session: Session,
    current_time: datetime,
) -> None:
    users = (
        database_session.query(User)
        .filter(
            User.reminder_hour == current_time.hour,
            User.reminder_minute == current_time.minute,
        )
        .all()
    )

    for user in users:
        active_habits = (
            database_session.query(Habit)
            .filter(
                Habit.user_id == user.id,
                Habit.active.is_(True),
            )
            .all()
        )

        pending_titles = []

        for habit in active_habits:
            completion = (
                database_session.query(HabitCompletion)
                .filter(
                    HabitCompletion.habit_id == habit.id,
                    HabitCompletion.completion_date == current_time.date(),
                )
                .first()
            )

            if completion is None:
                pending_titles.append(habit.title)

        if not pending_titles:
            logger.info(
                "Для пользователя %s нет невыполненных привычек.",
                user.telegram_id,
            )
            continue

        message_text = (
            "Напоминание о привычках:\n"
            + "\n".join(f"• {title}" for title in pending_titles)
            + "\n\nОткройте бота и отметьте выполнение."
        )

        try:
            bot.send_message(user.telegram_id, message_text)
            logger.info(
                "Напоминание отправлено пользователю %s.",
                user.telegram_id,
            )
        except Exception:
            logger.exception(
                "Не удалось отправить напоминание пользователю %s.",
                user.telegram_id,
            )


def prepare_next_day(
    database_session: Session,
    current_date: date,
) -> None:
    """Деактивирует привычки, достигшие целевого количества выполнений."""
    finished_habits = (
        database_session.query(Habit)
        .filter(
            Habit.active.is_(True),
            Habit.successful_completions >= Habit.target_completions,
        )
        .all()
    )

    for habit in finished_habits:
        habit.active = False
        logger.info("Привычка '%s' завершена.", habit.title)

    database_session.commit()
    logger.info("Проверка завершения привычек за %s выполнена.", current_date)


def run_notifier() -> None:
    last_processed_minute = None
    last_daily_rollover = None

    logger.info(
        "Notifier запущен. Часовой пояс напоминаний: %s. Интервал проверки: 5 секунд.",
        BAKU_TZ,
    )

    while True:
        current_time = datetime.now(BAKU_TZ)
        minute_key = current_time.strftime("%Y-%m-%d %H:%M")

        try:
            # Обрабатываем каждую минуту только один раз.
            # Это предотвращает повторные сообщения в течение одной минуты.
            if minute_key != last_processed_minute:
                database_session = SessionLocal()

                try:
                    send_due_reminders(database_session, current_time)

                    if (
                        current_time.hour == 0
                        and current_time.minute == 0
                        and last_daily_rollover != current_time.date()
                    ):
                        prepare_next_day(
                            database_session,
                            current_time.date(),
                        )
                        last_daily_rollover = current_time.date()

                    last_processed_minute = minute_key

                finally:
                    database_session.close()

        except Exception:
            logger.exception("Ошибка в цикле notifier.")

        time.sleep(5)


if __name__ == "__main__":
    run_notifier()
