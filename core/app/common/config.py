"""Configuration management - single source of truth for all environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class DatabaseConfig:
    """Database connection configuration."""

    # For DuckDB, we only need the database path
    database: str  # File path for DuckDB
    host: str = "localhost"  # Kept for compatibility
    port: int = 5432  # Kept for compatibility
    user: str = ""  # Not used for DuckDB
    password: str = ""  # Not used for DuckDB

    @property
    def dsn(self) -> str:
        """Database connection string (file path for DuckDB)."""
        return self.database


@dataclass
class TelegramConfig:
    """Telegram bot configuration."""

    bot_token: str
    chat_id: str


@dataclass
class APIConfig:
    """External API keys configuration."""

    rapidapi_key: str
    deepseek_api_key: str
    tushare_token: str | None = None
    alpaca_key: str | None = None
    alpaca_secret: str | None = None


@dataclass
class DataSourceConfig:
    """Data source preferences."""

    us_source: str = "yfinance"  # yfinance | alpaca
    cn_source: str = "tushare"  # tushare | akshare


@dataclass
class SchedulerConfig:
    """Scheduler and timezone configuration."""

    timezone: str = "Asia/Taipei"
    daily_report_time: str = "08:30"
    poll_interval: int = 60  # seconds


@dataclass
class AppConfig:
    """Main application configuration."""

    database: DatabaseConfig
    telegram: TelegramConfig
    api: APIConfig
    data_source: DataSourceConfig
    scheduler: SchedulerConfig
    environment: str = "development"

    @classmethod
    def from_env(cls) -> AppConfig:
        """Load configuration from environment variables."""
        # Database (DuckDB)
        db_config = DatabaseConfig(
            database=os.getenv("DB_PATH", "core/data/db/quant_os.duckdb"),
            host=os.getenv("DB_HOST", "localhost"),  # Kept for compatibility
            port=int(os.getenv("DB_PORT", "5432")),  # Kept for compatibility
            user=os.getenv("DB_USER", ""),
            password=os.getenv("DB_PASSWORD", ""),
        )

        # Telegram
        tg_config = TelegramConfig(
            bot_token=os.getenv("TG_BOT_TOKEN", ""),
            chat_id=os.getenv("TG_CHAT_ID", ""),
        )

        # API Keys
        api_config = APIConfig(
            rapidapi_key=os.getenv("RAPIDAPI_KEY", ""),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            tushare_token=os.getenv("TUSHARE_TOKEN"),
            alpaca_key=os.getenv("ALPACA_API_KEY"),
            alpaca_secret=os.getenv("ALPACA_API_SECRET"),
        )

        # Data Sources
        data_source_config = DataSourceConfig(
            us_source=os.getenv("US_DATA_SOURCE", "yfinance"),
            cn_source=os.getenv("CN_DATA_SOURCE", "tushare"),
        )

        # Scheduler
        scheduler_config = SchedulerConfig(
            timezone=os.getenv("TZ", "Asia/Taipei"),
            daily_report_time=os.getenv("DAILY_REPORT_TIME", "08:30"),
            poll_interval=int(os.getenv("POLL_INTERVAL", "60")),
        )

        return cls(
            database=db_config,
            telegram=tg_config,
            api=api_config,
            data_source=data_source_config,
            scheduler=scheduler_config,
            environment=os.getenv("ENVIRONMENT", "development"),
        )

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []

        # Check required fields
        if not self.telegram.bot_token:
            errors.append("TG_BOT_TOKEN is required")
        if not self.telegram.chat_id:
            errors.append("TG_CHAT_ID is required")
        if not self.api.deepseek_api_key:
            errors.append("DEEPSEEK_API_KEY is required")
        # DB_PASSWORD not required for DuckDB

        # Check data source specific keys
        if self.data_source.us_source == "alpaca":
            if not self.api.alpaca_key or not self.api.alpaca_secret:
                errors.append("ALPACA_API_KEY and ALPACA_API_SECRET required for Alpaca")
        if self.data_source.cn_source == "tushare":
            if not self.api.tushare_token:
                errors.append("TUSHARE_TOKEN required for Tushare")

        return errors

    def print_summary(self, mask_secrets: bool = True) -> str:
        """Print configuration summary (with secrets masked)."""

        def mask(value: str) -> str:
            if not value or not mask_secrets:
                return value
            return f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"

        lines = [
            "=== Configuration Summary ===",
            f"Environment: {self.environment}",
            "",
            "[Database]",
            "  Type: DuckDB",
            f"  Path: {self.database.database}",
            "",
            "[Telegram]",
            f"  Bot Token: {mask(self.telegram.bot_token)}",
            f"  Chat ID: {self.telegram.chat_id}",
            "",
            "[API Keys]",
            f"  RapidAPI: {mask(self.api.rapidapi_key)}",
            f"  DeepSeek: {mask(self.api.deepseek_api_key)}",
            f"  Tushare: {mask(self.api.tushare_token or 'Not set')}",
            "",
            "[Data Sources]",
            f"  US Market: {self.data_source.us_source}",
            f"  CN Market: {self.data_source.cn_source}",
            "",
            "[Scheduler]",
            f"  Timezone: {self.scheduler.timezone}",
            f"  Daily Report: {self.scheduler.daily_report_time}",
            "============================",
        ]
        return "\n".join(lines)


# Global config instance
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Get or create global configuration instance."""
    global _config
    if _config is None:
        _config = AppConfig.from_env()
    return _config


def reload_config() -> AppConfig:
    """Force reload configuration from environment."""
    global _config
    _config = AppConfig.from_env()
    return _config
