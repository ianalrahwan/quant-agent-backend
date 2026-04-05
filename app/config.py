from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "quant-agent-backend"
    debug: bool = False

    # Database
    database_url: str

    # Redis
    redis_url: str

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Anthropic
    anthropic_api_key: str | None = None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
