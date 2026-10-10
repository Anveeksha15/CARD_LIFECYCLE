from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    webhook_secret: str = "change-me-dev-secret"
    settlement_delay_seconds: int = 5
    gateway_port: int = 8000


settings = Settings()
