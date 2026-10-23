from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reminder_hour: Mapped[int] = mapped_column(Integer, default=20)
    reminder_minute: Mapped[int] = mapped_column(Integer, default=0)
    habits: Mapped[list["Habit"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Habit(Base):
    __tablename__ = "habits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    successful_completions: Mapped[int] = mapped_column(Integer, default=0)
    target_completions: Mapped[int] = mapped_column(Integer, default=21)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user: Mapped[User] = relationship(back_populates="habits")
    completions: Mapped[list["HabitCompletion"]] = relationship(back_populates="habit", cascade="all, delete-orphan")


class HabitCompletion(Base):
    __tablename__ = "habit_completions"
    __table_args__ = (UniqueConstraint("habit_id", "completion_date", name="uq_habit_completion_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    habit_id: Mapped[int] = mapped_column(ForeignKey("habits.id", ondelete="CASCADE"), index=True)
    completion_date: Mapped[date] = mapped_column(Date, default=date.today)
    completed: Mapped[bool] = mapped_column(Boolean)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    habit: Mapped[Habit] = relationship(back_populates="completions")
