from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://habits_user:change_me@localhost:5432/habits_db"
    telegram_bot_token: str
    jwt_secret_key: str
    bot_auth_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    habit_completion_target: int = 21
    reminder_check_seconds: int = 60
    default_reminder_hour: int = 20
    default_reminder_minute: int = 0
    api_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
