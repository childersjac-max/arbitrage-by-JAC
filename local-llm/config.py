"""Environment-driven settings for the local inference client."""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from paths import ENV_FILE

# Used only if prompts/system_default.txt is missing
_FALLBACK_SYSTEM = "You are a helpful assistant. Follow the user instructions precisely."


class Backend(str, Enum):
    OLLAMA = "ollama"
    VLLM = "vllm"
    OPENAI_COMPAT = "openai_compat"


class LocalLLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    local_llm_backend: Backend = Field(default=Backend.OLLAMA, validation_alias="LOCAL_LLM_BACKEND")

    ollama_host: str = Field(default="http://127.0.0.1:11434", validation_alias="OLLAMA_HOST")
    ollama_model: str = Field(
        default="qwen2.5:3b-instruct-q4_K_M",
        validation_alias="OLLAMA_MODEL",
    )
    ollama_model_fast: str = Field(
        default="qwen2.5:1.5b-instruct-q4_K_M",
        validation_alias="OLLAMA_MODEL_FAST",
    )
    ollama_model_balanced: str = Field(
        default="qwen2.5:3b-instruct-q4_K_M",
        validation_alias="OLLAMA_MODEL_BALANCED",
    )
    ollama_model_quality: str = Field(
        default="qwen2.5-coder:7b-instruct-q4_K_M",
        validation_alias="OLLAMA_MODEL_QUALITY",
    )

    vllm_base_url: str = Field(default="http://127.0.0.1:8000/v1", validation_alias="VLLM_BASE_URL")
    vllm_model: str = Field(
        default="meta-llama/Llama-3.3-70B-Instruct",
        validation_alias="VLLM_MODEL",
    )

    local_llm_temperature: float = Field(default=0.0, validation_alias="LOCAL_LLM_TEMPERATURE")
    local_llm_max_tokens: int = Field(default=512, validation_alias="LOCAL_LLM_MAX_TOKENS")
    local_llm_timeout_sec: float = Field(default=45.0, validation_alias="LOCAL_LLM_TIMEOUT_SEC")
    local_llm_prompt_timeout_sec: float = Field(
        default=600.0,
        validation_alias="LOCAL_LLM_PROMPT_TIMEOUT_SEC",
    )
    local_llm_max_retries: int = Field(default=3, validation_alias="LOCAL_LLM_MAX_RETRIES")

    local_llm_max_connections: int = Field(default=32, validation_alias="LOCAL_LLM_MAX_CONNECTIONS")
    local_llm_batch_concurrency: int = Field(
        default=1,
        validation_alias="LOCAL_LLM_BATCH_CONCURRENCY",
    )

    # Free-form prompting (prompt_cli.py, prompt_server.py, complete())
    local_llm_prompt_max_tokens: int = Field(
        default=4096,
        validation_alias="LOCAL_LLM_PROMPT_MAX_TOKENS",
    )
    local_llm_prompt_temperature: float = Field(
        default=0.2,
        validation_alias="LOCAL_LLM_PROMPT_TEMPERATURE",
    )
    local_llm_default_system: str = Field(
        default=_FALLBACK_SYSTEM,
        validation_alias="LOCAL_LLM_DEFAULT_SYSTEM",
    )
    local_llm_prompt_server_host: str = Field(
        default="127.0.0.1",
        validation_alias="LOCAL_LLM_PROMPT_SERVER_HOST",
    )
    local_llm_prompt_server_port: int = Field(
        default=5050,
        validation_alias="LOCAL_LLM_PROMPT_SERVER_PORT",
    )
    local_llm_ui_host: str = Field(default="127.0.0.1", validation_alias="LOCAL_LLM_UI_HOST")
    local_llm_ui_port: int = Field(default=7860, validation_alias="LOCAL_LLM_UI_PORT")
    local_llm_ui_lan: bool = Field(default=False, validation_alias="LOCAL_LLM_UI_LAN")
    local_llm_ui_timeout_sec: float = Field(
        default=900.0,
        validation_alias="LOCAL_LLM_UI_TIMEOUT_SEC",
    )
    local_llm_ui_max_tokens: int = Field(
        default=512,
        validation_alias="LOCAL_LLM_UI_MAX_TOKENS",
    )

    # Performance profile: fast | balanced | quality (single switch for CPU tuning)
    local_llm_performance_profile: str = Field(
        default="balanced",
        validation_alias="LOCAL_LLM_PERFORMANCE_PROFILE",
    )
    local_llm_default_chat_mode: str = Field(
        default="balanced",
        validation_alias="LOCAL_LLM_DEFAULT_CHAT_MODE",
    )
    # Profile: FAST
    profile_fast_max_tokens: int = Field(default=192, validation_alias="PROFILE_FAST_MAX_TOKENS")
    profile_fast_max_tokens_cap: int = Field(
        default=384, validation_alias="PROFILE_FAST_MAX_TOKENS_CAP"
    )
    profile_fast_num_ctx: int = Field(default=768, validation_alias="PROFILE_FAST_NUM_CTX")
    profile_fast_max_history: int = Field(default=1, validation_alias="PROFILE_FAST_MAX_HISTORY")
    profile_fast_timeout_sec: float = Field(default=300.0, validation_alias="PROFILE_FAST_TIMEOUT_SEC")
    profile_fast_temperature: float = Field(default=0.2, validation_alias="PROFILE_FAST_TEMPERATURE")
    profile_fast_system_prompt_file: str = Field(
        default="prompts/system_fast.txt",
        validation_alias="PROFILE_FAST_SYSTEM_PROMPT_FILE",
    )
    # Profile: BALANCED
    profile_balanced_max_tokens: int = Field(
        default=384, validation_alias="PROFILE_BALANCED_MAX_TOKENS"
    )
    profile_balanced_max_tokens_cap: int = Field(
        default=768, validation_alias="PROFILE_BALANCED_MAX_TOKENS_CAP"
    )
    profile_balanced_num_ctx: int = Field(
        default=1536, validation_alias="PROFILE_BALANCED_NUM_CTX"
    )
    profile_balanced_max_history: int = Field(
        default=2, validation_alias="PROFILE_BALANCED_MAX_HISTORY"
    )
    profile_balanced_timeout_sec: float = Field(
        default=480.0, validation_alias="PROFILE_BALANCED_TIMEOUT_SEC"
    )
    profile_balanced_temperature: float = Field(
        default=0.2, validation_alias="PROFILE_BALANCED_TEMPERATURE"
    )
    profile_balanced_system_prompt_file: str = Field(
        default="prompts/system_balanced.txt",
        validation_alias="PROFILE_BALANCED_SYSTEM_PROMPT_FILE",
    )
    # Profile: QUALITY
    profile_quality_max_tokens: int = Field(
        default=512, validation_alias="PROFILE_QUALITY_MAX_TOKENS"
    )
    profile_quality_max_tokens_cap: int = Field(
        default=1024, validation_alias="PROFILE_QUALITY_MAX_TOKENS_CAP"
    )
    profile_quality_num_ctx: int = Field(
        default=2048, validation_alias="PROFILE_QUALITY_NUM_CTX"
    )
    profile_quality_max_history: int = Field(
        default=3, validation_alias="PROFILE_QUALITY_MAX_HISTORY"
    )
    profile_quality_timeout_sec: float = Field(
        default=900.0, validation_alias="PROFILE_QUALITY_TIMEOUT_SEC"
    )
    profile_quality_temperature: float = Field(
        default=0.2, validation_alias="PROFILE_QUALITY_TEMPERATURE"
    )
    profile_quality_system_prompt_file: str = Field(
        default="prompts/system_default.txt",
        validation_alias="PROFILE_QUALITY_SYSTEM_PROMPT_FILE",
    )
    # Legacy chat mode keys (mapped to profiles if still in ui_state.json)
    local_llm_fast_max_tokens: int = Field(
        default=256,
        validation_alias="LOCAL_LLM_FAST_MAX_TOKENS",
    )
    local_llm_fast_max_tokens_cap: int = Field(
        default=512,
        validation_alias="LOCAL_LLM_FAST_MAX_TOKENS_CAP",
    )
    local_llm_fast_num_ctx: int = Field(default=1024, validation_alias="LOCAL_LLM_FAST_NUM_CTX")
    local_llm_fast_max_history: int = Field(default=2, validation_alias="LOCAL_LLM_FAST_MAX_HISTORY")
    local_llm_fast_timeout_sec: float = Field(
        default=600.0,
        validation_alias="LOCAL_LLM_FAST_TIMEOUT_SEC",
    )
    local_llm_fast_temperature: float = Field(
        default=0.2,
        validation_alias="LOCAL_LLM_FAST_TEMPERATURE",
    )
    local_llm_fast_system_prompt_file: str = Field(
        default="prompts/system_fast.txt",
        validation_alias="LOCAL_LLM_FAST_SYSTEM_PROMPT_FILE",
    )
    local_llm_normal_max_tokens: int = Field(
        default=512,
        validation_alias="LOCAL_LLM_NORMAL_MAX_TOKENS",
    )
    local_llm_normal_max_tokens_cap: int = Field(
        default=2048,
        validation_alias="LOCAL_LLM_NORMAL_MAX_TOKENS_CAP",
    )
    local_llm_normal_num_ctx: int = Field(
        default=2048,
        validation_alias="LOCAL_LLM_NORMAL_NUM_CTX",
    )
    local_llm_normal_max_history: int = Field(
        default=4,
        validation_alias="LOCAL_LLM_NORMAL_MAX_HISTORY",
    )
    local_llm_normal_timeout_sec: float = Field(
        default=900.0,
        validation_alias="LOCAL_LLM_NORMAL_TIMEOUT_SEC",
    )
    local_llm_normal_temperature: float = Field(
        default=0.2,
        validation_alias="LOCAL_LLM_NORMAL_TEMPERATURE",
    )
    local_llm_normal_system_prompt_file: str = Field(
        default="prompts/system_default.txt",
        validation_alias="LOCAL_LLM_NORMAL_SYSTEM_PROMPT_FILE",
    )

    # Ollama tuning for 8B (larger context + steadier codegen)
    ollama_num_ctx: int = Field(default=2048, validation_alias="OLLAMA_NUM_CTX")
    ollama_chat_num_ctx: int = Field(default=1536, validation_alias="OLLAMA_CHAT_NUM_CTX")
    ollama_num_thread: int | None = Field(default=None, validation_alias="OLLAMA_NUM_THREAD")
    ollama_top_p: float = Field(default=0.9, validation_alias="OLLAMA_TOP_P")
    ollama_repeat_penalty: float = Field(default=1.1, validation_alias="OLLAMA_REPEAT_PENALTY")

    # Multi-phase architect (large prompts)
    architect_max_phases: int = Field(default=5, validation_alias="ARCHITECT_MAX_PHASES")
    architect_plan_max_tokens: int = Field(default=1024, validation_alias="ARCHITECT_PLAN_MAX_TOKENS")
    architect_phase_max_tokens: int = Field(default=2048, validation_alias="ARCHITECT_PHASE_MAX_TOKENS")
    architect_temperature: float = Field(default=0.15, validation_alias="ARCHITECT_TEMPERATURE")

    def resolved_model(self) -> str:
        if self.local_llm_backend == Backend.OLLAMA:
            return self.ollama_model
        return self.vllm_model

    def resolved_base_url(self) -> str:
        if self.local_llm_backend == Backend.OLLAMA:
            return self.ollama_host.rstrip("/")
        return self.vllm_base_url.rstrip("/")


@lru_cache
def get_settings() -> LocalLLMSettings:
    return LocalLLMSettings()


def reload_settings() -> LocalLLMSettings:
    get_settings.cache_clear()
    return get_settings()
