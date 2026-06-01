"""Environment-driven settings for the harvester pipeline."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from paths import ENV_FILE


class HarvesterSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    odds_api_key: str = Field(default="", validation_alias="ODDS_API_KEY")
    odds_api_base_url: str = Field(
        default="https://api.the-odds-api.com",
        validation_alias="ODDS_API_BASE_URL",
    )
    odds_api_regions: str = Field(default="us", validation_alias="ODDS_API_REGIONS")
    odds_api_markets: str = Field(default="h2h", validation_alias="ODDS_API_MARKETS")
    odds_api_odds_format: str = Field(default="decimal", validation_alias="ODDS_API_ODDS_FORMAT")
    default_sport_key: str = Field(
        default="basketball_nba",
        validation_alias="HARVESTER_DEFAULT_SPORT",
    )
    http_timeout_sec: float = Field(default=30.0, validation_alias="HARVESTER_HTTP_TIMEOUT_SEC")
    min_arb_yield_pct: float = Field(
        default=0.1,
        validation_alias="HARVESTER_MIN_ARB_YIELD_PCT",
    )
    use_local_normalization: bool = Field(
        default=True,
        validation_alias="HARVESTER_USE_LOCAL_NORMALIZATION",
    )


@lru_cache
def get_settings() -> HarvesterSettings:
    return HarvesterSettings()
