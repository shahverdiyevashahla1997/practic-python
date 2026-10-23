from datetime import date

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_database_session
from app.models import Habit, HabitCompletion, User
from app.schemas import CompletionResponse, HabitCreate, HabitResponse, HabitUpdate, ReminderSettings, TokenResponse
from app.security import create_access_token, get_current_user

app = FastAPI(title="Habit Tracker API", version="1.0.0")


@app.get("/health")
def get_health_status():
    return {"status": "ok"}


@app.post("/auth/telegram/{telegram_id}", response_model=TokenResponse)
def authenticate_telegram_user(telegram_id: int, x_bot_auth_secret: str | None = Header(default=None), database_session: Session = Depends(get_database_session)):
    """Issue a JWT only to the trusted bot service."""
    if x_bot_auth_secret is None or x_bot_auth_secret != settings.bot_auth_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bot authentication failed")
    if telegram_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid Telegram ID")
    user = database_session.query(User).filter(User.telegram_id == telegram_id).first()
    if user is None:
        user = User(telegram_id=telegram_id, reminder_hour=settings.default_reminder_hour,
                    reminder_minute=settings.default_reminder_minute)
        database_session.add(user)
        database_session.commit()
    access_token, expires_at = create_access_token(telegram_id)
    return {"access_token": access_token, "expires_at": expires_at}


@app.get("/habits", response_model=list[HabitResponse])
def list_habits(current_user: User = Depends(get_current_user), database_session: Session = Depends(get_database_session)):
    return database_session.query(Habit).filter(Habit.user_id == current_user.id, Habit.active.is_(True)).order_by(Habit.id).all()


@app.post("/habits", response_model=HabitResponse, status_code=status.HTTP_201_CREATED)
def create_habit(habit_data: HabitCreate, current_user: User = Depends(get_current_user), database_session: Session = Depends(get_database_session)):
    habit = Habit(user_id=current_user.id, title=habit_data.title.strip(), description=habit_data.description.strip(),
                  target_completions=habit_data.target_completions)
    if not habit.title:
        raise HTTPException(status_code=422, detail="Habit title cannot be empty")
    database_session.add(habit)
    database_session.commit()
    database_session.refresh(habit)
    return habit


@app.patch("/habits/{habit_id}", response_model=HabitResponse)
def update_habit(habit_id: int, habit_data: HabitUpdate, current_user: User = Depends(get_current_user), database_session: Session = Depends(get_database_session)):
    habit = database_session.query(Habit).filter(Habit.id == habit_id, Habit.user_id == current_user.id).first()
    if habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    for field_name, field_value in habit_data.model_dump(exclude_unset=True).items():
        setattr(habit, field_name, field_value)
    if isinstance(habit.title, str):
        habit.title = habit.title.strip()
        if not habit.title:
            raise HTTPException(status_code=422, detail="Habit title cannot be empty")
    database_session.commit()
    database_session.refresh(habit)
    return habit


@app.delete("/habits/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_habit(habit_id: int, current_user: User = Depends(get_current_user), database_session: Session = Depends(get_database_session)):
    habit = database_session.query(Habit).filter(Habit.id == habit_id, Habit.user_id == current_user.id).first()
    if habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    database_session.delete(habit)
    database_session.commit()
    return None


@app.put("/habits/{habit_id}/completion", response_model=CompletionResponse)
def mark_habit_completion(habit_id: int, completed: bool, current_user: User = Depends(get_current_user), database_session: Session = Depends(get_database_session)):
    habit = database_session.query(Habit).filter(Habit.id == habit_id, Habit.user_id == current_user.id, Habit.active.is_(True)).first()
    if habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    current_date = date.today()
    completion = database_session.query(HabitCompletion).filter(HabitCompletion.habit_id == habit.id,
                                                                  HabitCompletion.completion_date == current_date).first()
    previous_completed = completion.completed if completion else False
    if completion is None:
        completion = HabitCompletion(habit_id=habit.id, completion_date=current_date, completed=completed)
        database_session.add(completion)
    else:
        completion.completed = completed
    if completed and not previous_completed:
        habit.successful_completions += 1
    elif previous_completed and not completed:
        habit.successful_completions = max(0, habit.successful_completions - 1)
    if habit.successful_completions >= habit.target_completions:
        habit.active = False
    database_session.commit()
    return {"habit_id": habit.id, "completion_date": current_date, "completed": completed}


@app.get("/habits/{habit_id}/completion", response_model=CompletionResponse)
def get_today_completion(habit_id: int, current_user: User = Depends(get_current_user), database_session: Session = Depends(get_database_session)):
    habit = database_session.query(Habit).filter(Habit.id == habit_id, Habit.user_id == current_user.id).first()
    if habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    completion = database_session.query(HabitCompletion).filter(HabitCompletion.habit_id == habit.id,
                                                                  HabitCompletion.completion_date == date.today()).first()
    if completion is None:
        raise HTTPException(status_code=404, detail="No completion recorded for today")
    return completion


@app.put("/settings/reminder", status_code=status.HTTP_200_OK)
def update_reminder_settings(reminder_settings: ReminderSettings, current_user: User = Depends(get_current_user), database_session: Session = Depends(get_database_session)):
    current_user.reminder_hour = reminder_settings.hour
    current_user.reminder_minute = reminder_settings.minute
    database_session.commit()
    return {"hour": current_user.reminder_hour, "minute": current_user.reminder_minute}
