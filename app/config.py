from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "quant-agent-backend"
    debug: bool = False

    # Database
    database_url: str | None = None
    db_host: str | None = None
    db_port: int = 5432
    db_name: str = "quant_agent"
    db_user: str = "quantagent"
    db_password: str | None = None

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        if self.db_host and self.db_password:
            return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?ssl=require"
        raise ValueError("Either DATABASE_URL or DB_HOST + DB_PASSWORD must be set")

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "https://quant-agent-service.vercel.app",
        "https://quant-agent-service-ianalrahwans-projects.vercel.app",
    ]

    # Anthropic
    anthropic_api_key: str | None = None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
