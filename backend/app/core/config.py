from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "نظام المحاسبة"
    database_url: str = "postgresql+psycopg://accounting:accounting_dev_password@localhost:5432/accounting"
    access_token_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
