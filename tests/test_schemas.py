import pytest
from pydantic import ValidationError

from app.schemas import HabitCreate, ReminderSettings


def test_habit_create_accepts_valid_input():
    habit = HabitCreate(title="Read", description="Read for ten minutes", target_completions=21)
    assert habit.title == "Read"
    assert habit.target_completions == 21


def test_habit_create_rejects_empty_title():
    with pytest.raises(ValidationError):
        HabitCreate(title="")


def test_reminder_settings_reject_invalid_hour():
    with pytest.raises(ValidationError):
        ReminderSettings(hour=25, minute=0)
