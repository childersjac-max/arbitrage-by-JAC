"""Environment-driven settings for the harvester pipeline."""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from harvester_paths import ENV_FILE


class HarvesterSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    odds_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ODDS_API_KEY", "THE_ODDS_API_KEY"),
    )
    odds_api_base_url: str = Field(
        default="https://api.the-odds-api.com",
        validation_alias="ODDS_API_BASE_URL",
    )
    odds_api_regions: str = Field(default="us", validation_alias="ODDS_API_REGIONS")
    odds_api_markets: str = Field(
        default="h2h,spreads,totals",
        validation_alias="ODDS_API_MARKETS",
    )
    odds_api_odds_format: str = Field(default="decimal", validation_alias="ODDS_API_ODDS_FORMAT")
    odds_provider: str = Field(
        default="odds_api",
        validation_alias="HARVESTER_ODDS_PROVIDER",
        description="odds_api | perplexity | auto",
    )
    perplexity_api_key: str = Field(default="", validation_alias="PERPLEXITY_API_KEY")
    perplexity_base_url: str = Field(
        default="https://api.perplexity.ai",
        validation_alias="PERPLEXITY_BASE_URL",
    )
    perplexity_model: str = Field(default="sonar-pro", validation_alias="PERPLEXITY_MODEL")
    perplexity_max_tokens: int = Field(
        default=12000,
        validation_alias="PERPLEXITY_MAX_TOKENS",
    )
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
        default=False,
        validation_alias="HARVESTER_USE_LOCAL_NORMALIZATION",
    )
    use_llm_arbitrage: bool = Field(
        default=False,
        validation_alias="HARVESTER_USE_LLM_ARBITRAGE",
    )
    dashboard_fast_mode: bool = Field(
        default=True,
        validation_alias="HARVESTER_DASHBOARD_FAST_MODE",
    )
    llm_arb_max_events: int = Field(default=25, validation_alias="HARVESTER_LLM_ARB_MAX_EVENTS")
    llm_arb_max_tokens: int = Field(default=4096, validation_alias="HARVESTER_LLM_ARB_MAX_TOKENS")
    harvester_ui_host: str = Field(default="127.0.0.1", validation_alias="HARVESTER_UI_HOST")
    harvester_ui_port: int = Field(default=8765, validation_alias="HARVESTER_UI_PORT")
    dashboard_timezone: str = Field(
        default="America/New_York",
        validation_alias="HARVESTER_TIMEZONE",
    )
    run_timeout_sec: float = Field(
        default=120.0,
        validation_alias="HARVESTER_RUN_TIMEOUT_SEC",
    )
    balance_provider: str = Field(
        default="mock",
        validation_alias="HARVESTER_BALANCE_PROVIDER",
    )
    pikkit_api_key: str = Field(default="", validation_alias="PIKKIT_API_KEY")
    min_leg_stake_usd: float = Field(
        default=1.0,
        validation_alias="HARVESTER_MIN_LEG_STAKE_USD",
    )
    min_allocation_profit_usd: float = Field(
        default=0.5,
        validation_alias="HARVESTER_MIN_ALLOCATION_PROFIT_USD",
    )
    min_allocation_roi_pct: float = Field(
        default=0.1,
        validation_alias="HARVESTER_MIN_ALLOCATION_ROI_PCT",
    )
    alloc_weight_profit: float = Field(
        default=1.0,
        validation_alias="HARVESTER_ALLOC_WEIGHT_PROFIT",
    )
    alloc_weight_roi: float = Field(
        default=0.25,
        validation_alias="HARVESTER_ALLOC_WEIGHT_ROI",
    )
    alloc_weight_capital_penalty: float = Field(
        default=0.15,
        validation_alias="HARVESTER_ALLOC_WEIGHT_CAPITAL_PENALTY",
    )
    http_proxy_url: str | None = Field(default=None, validation_alias="HARVESTER_HTTP_PROXY")
    http_user_agent: str = Field(
        default="harvester/1.0",
        validation_alias="HARVESTER_HTTP_USER_AGENT",
    )

    def effective_odds_provider(self) -> str:
        raw = (self.odds_provider or "odds_api").strip().lower()
        if raw in ("perplexity", "odds_api"):
            return raw
        if self.odds_api_key.strip():
            return "odds_api"
        if self.perplexity_api_key.strip():
            return "perplexity"
        return "odds_api"

    def odds_source_configured(self) -> bool:
        if self.effective_odds_provider() == "perplexity":
            return bool(self.perplexity_api_key.strip())
        return bool(self.odds_api_key.strip())

    def odds_gateway_key(self) -> str:
        return "perplexity_odds" if self.effective_odds_provider() == "perplexity" else "the_odds_api"

    def odds_gateway_label(self) -> str:
        return (
            "Perplexity Sonar"
            if self.effective_odds_provider() == "perplexity"
            else "The Odds API"
        )


@lru_cache
def get_settings() -> HarvesterSettings:
    return HarvesterSettings()
