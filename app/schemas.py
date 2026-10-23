from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict


class HabitCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    target_completions: int = Field(default=21, ge=1, le=3650)


class HabitUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    active: bool | None = None
    target_completions: int | None = Field(default=None, ge=1, le=3650)


class HabitResponse(BaseModel):
    id: int
    title: str
    description: str
    active: bool
    successful_completions: int
    target_completions: int
    model_config = ConfigDict(from_attributes=True)


class CompletionResponse(BaseModel):
    habit_id: int
    completion_date: date
    completed: bool


class ReminderSettings(BaseModel):
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
