from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "Vantage"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"
    log_format: str = "json"
    api_prefix: str = "/api/v1"

    api_keys: list[str] = Field(default=["dev-local-key"])
    github_webhook_secret: str | None = None

    olap_backend: str = "duckdb"
    duckdb_path: Path = Path("./data/vantage.duckdb")
    database_url: str = "sqlite+aiosqlite:///./data/registry.db"

    anomaly_interval_minutes: int = 15
    rollup_interval_minutes: int = 60
    anomaly_window_days: int = 7

    default_warn_z: float = 2.0
    default_crit_z: float = 3.0
    default_rate_change_factor: float = 1.5
    default_error_rate_pct: float = 5.0
    default_cost_threshold_usd: float | None = None

    slack_webhook_url: str | None = None
    enable_prompt_logging: bool = False

    cost_model_path: Path = Path("./vantage/data/model_prices.json")
    grafana_port: int = 3000


@lru_cache
def get_settings() -> Settings:
    return Settings()
