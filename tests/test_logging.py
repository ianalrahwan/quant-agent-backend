import structlog

from app.logging import setup_logging


def test_setup_logging_configures_structlog():
    setup_logging()
    logger = structlog.get_logger("test")
    # Should not raise — logger is configured and callable
    assert logger is not None


def test_setup_logging_json_in_production():
    setup_logging(json_logs=True)
    config = structlog.get_config()
    processors = config["processors"]
    processor_names = [p.__name__ if hasattr(p, "__name__") else str(p) for p in processors]
    # JSON renderer should be in the chain
    assert any("JSON" in name or "json" in name.lower() for name in processor_names)
