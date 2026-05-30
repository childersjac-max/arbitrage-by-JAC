"""Runtime settings for the harvester pipeline."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class HarvesterSettings(BaseSettings):
    """Settings loaded from environment variables and optional `.env` files."""

    model_config = SettingsConfigDict(
        env_file=(".env", "local-llm/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    the_odds_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("THE_ODDS_API_KEY", "ODDSJAM_API_KEY", "ODDS_API_KEY"),
        description="Paid The Odds API key. ODDSJAM_API_KEY is accepted for compatibility.",
    )
    harvester_sports: list[str] = Field(
        default_factory=lambda: ["basketball_nba", "americanfootball_nfl"],
        validation_alias=AliasChoices("HARVESTER_SPORTS", "THE_ODDS_API_SPORTS"),
    )
    harvester_markets: list[str] = Field(
        default_factory=lambda: ["h2h", "spreads", "totals"],
        validation_alias=AliasChoices("HARVESTER_MARKETS", "THE_ODDS_API_MARKETS"),
    )
    harvester_regions: str = Field(default="us", validation_alias="HARVESTER_REGIONS")
    harvester_poll_interval_seconds: float = Field(
        default=30.0,
        validation_alias="HARVESTER_POLL_INTERVAL_SECONDS",
    )
    harvester_adapter_timeout_seconds: float = Field(
        default=15.0,
        validation_alias="HARVESTER_ADAPTER_TIMEOUT_SECONDS",
    )
    harvester_retry_attempts: int = Field(default=3, validation_alias="HARVESTER_RETRY_ATTEMPTS")
    harvester_retry_base_seconds: float = Field(
        default=0.5,
        validation_alias="HARVESTER_RETRY_BASE_SECONDS",
    )
    harvester_cache_path: Path = Field(
        default=Path(".cache/harvester/normalize_cache.sqlite3"),
        validation_alias="HARVESTER_NORMALIZE_CACHE_PATH",
    )
    harvester_reference_path: Path | None = Field(
        default=None,
        validation_alias="HARVESTER_REFERENCE_PATH",
    )
    harvester_output_path: Path | None = Field(default=None, validation_alias="HARVESTER_OUTPUT_PATH")
    harvester_pretty_json: bool = Field(default=True, validation_alias="HARVESTER_PRETTY_JSON")
    harvester_merge_start_window_minutes: int = Field(
        default=30,
        validation_alias="HARVESTER_MERGE_START_WINDOW_MINUTES",
    )
    harvester_enable_polymarket: bool = Field(
        default=False,
        validation_alias="HARVESTER_ENABLE_POLYMARKET",
    )
    polymarket_clob_base_url: str = Field(
        default="https://clob.polymarket.com",
        validation_alias="POLYMARKET_CLOB_BASE_URL",
    )
    local_llm_base_url: str = Field(default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL")
    local_llm_model: str = Field(default="llama3.1", validation_alias="OLLAMA_MODEL")
    local_llm_timeout_seconds: float = Field(default=20.0, validation_alias="LOCAL_LLM_TIMEOUT_SECONDS")
    local_llm_batch_size: int = Field(default=32, validation_alias="LOCAL_LLM_BATCH_SIZE")

    @field_validator("harvester_sports", "harvester_markets", mode="before")
    @classmethod
    def split_csv(cls, value: object) -> object:
        """Allow comma-delimited env vars for list settings."""

        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> HarvesterSettings:
    """Return cached harvester settings."""

    return HarvesterSettings()
