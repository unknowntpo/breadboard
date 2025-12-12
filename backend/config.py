"""Configuration management using python-dotenv."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class ClickHouseConfig:
    """ClickHouse connection configuration."""
    HOST: str = os.getenv("CLICKHOUSE_HOST", "localhost")
    PORT: int = int(os.getenv("CLICKHOUSE_PORT", "9000"))
    DATABASE: str = os.getenv("CLICKHOUSE_DB", "breadboard")
    USER: str = os.getenv("CLICKHOUSE_USER", "default")
    PASSWORD: str = os.getenv("CLICKHOUSE_PASSWORD", "")


class AppConfig:
    """Application configuration."""
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")


# Singleton instances
clickhouse_config = ClickHouseConfig()
app_config = AppConfig()
