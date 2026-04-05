from app.config import Settings


def test_settings_defaults():
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
    )
    assert settings.app_name == "quant-agent-backend"
    assert settings.debug is False
    assert settings.cors_origins == ["http://localhost:3000"]
    assert settings.anthropic_api_key is None


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/prod")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-123")
    monkeypatch.setenv("CORS_ORIGINS", '["https://my-app.vercel.app"]')
    monkeypatch.setenv("DEBUG", "true")

    settings = Settings()
    assert settings.database_url == "postgresql+asyncpg://u:p@db:5432/prod"
    assert settings.redis_url == "redis://redis:6379/0"
    assert settings.anthropic_api_key == "sk-test-123"
    assert settings.cors_origins == ["https://my-app.vercel.app"]
    assert settings.debug is True
