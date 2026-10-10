from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    webhook_secret: str = "change-me-dev-secret"
    settlement_delay_seconds: int = 5

    gateway_port: int = 8000
    acquirer_port: int = 8001
    processor_port: int = 8002
    network_port: int = 8003
    issuer_port: int = 8004

    acquirer_url: str = "http://localhost:8001"
    processor_url: str = "http://localhost:8002"
    network_url: str = "http://localhost:8003"
    issuer_url: str = "http://localhost:8004"


settings = Settings()
