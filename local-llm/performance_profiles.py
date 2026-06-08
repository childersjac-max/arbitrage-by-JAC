"""
CPU-optimized performance profiles for Ollama on Windows.

Switch with one variable in local-llm/.env:

    LOCAL_LLM_PERFORMANCE_PROFILE=fast      # interactive, lowest latency
    LOCAL_LLM_PERFORMANCE_PROFILE=balanced  # recommended default
    LOCAL_LLM_PERFORMANCE_PROFILE=quality   # 7B coder, slowest

Or run:  scripts/set-profile.bat balanced
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from config import LocalLLMSettings, get_settings
from prompt_loader import load_prompt_file


class PerformanceProfileName(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    QUALITY = "quality"


@dataclass(frozen=True)
class PerformanceProfile:
    name: PerformanceProfileName
    label: str
    summary: str
    ollama_model: str
    max_tokens: int
    max_tokens_cap: int
    num_ctx: int
    max_history_turns: int
    timeout_sec: float
    temperature: float
    system_prompt_relpath: str
    batch_concurrency: int
    architect_max_phases: int
    architect_enabled: bool
    warm_on_send: bool
    ollama_num_ctx_cap: int
    normalize_max_tokens: int
    allow_parallel_normalize: bool

    @property
    def use_fast_model_picker(self) -> bool:
        return self.name == PerformanceProfileName.FAST


def parse_performance_profile(value: str | None) -> PerformanceProfileName:
    if not value:
        return PerformanceProfileName.BALANCED
    key = value.strip().lower()
    for member in PerformanceProfileName:
        if key == member.value:
            return member
    return PerformanceProfileName.BALANCED


def _profile(name: PerformanceProfileName, cfg: LocalLLMSettings) -> PerformanceProfile:
    if name == PerformanceProfileName.FAST:
        return PerformanceProfile(
            name=name,
            label="Fast",
            summary="1.5B-class model, minimal context. Target: sub-2 min replies on CPU.",
            ollama_model=cfg.ollama_model_fast,
            max_tokens=cfg.profile_fast_max_tokens,
            max_tokens_cap=cfg.profile_fast_max_tokens_cap,
            num_ctx=cfg.profile_fast_num_ctx,
            max_history_turns=cfg.profile_fast_max_history,
            timeout_sec=cfg.profile_fast_timeout_sec,
            temperature=cfg.profile_fast_temperature,
            system_prompt_relpath=cfg.profile_fast_system_prompt_file,
            batch_concurrency=1,
            architect_max_phases=0,
            architect_enabled=False,
            warm_on_send=True,
            ollama_num_ctx_cap=cfg.profile_fast_num_ctx,
            normalize_max_tokens=256,
            allow_parallel_normalize=False,
        )
    if name == PerformanceProfileName.QUALITY:
        return PerformanceProfile(
            name=name,
            label="Quality",
            summary="7B coder model, larger context. Use when accuracy matters; avoid mixing with batch jobs.",
            ollama_model=cfg.ollama_model_quality,
            max_tokens=cfg.profile_quality_max_tokens,
            max_tokens_cap=cfg.profile_quality_max_tokens_cap,
            num_ctx=cfg.profile_quality_num_ctx,
            max_history_turns=cfg.profile_quality_max_history,
            timeout_sec=cfg.profile_quality_timeout_sec,
            temperature=cfg.profile_quality_temperature,
            system_prompt_relpath=cfg.profile_quality_system_prompt_file,
            batch_concurrency=1,
            architect_max_phases=cfg.architect_max_phases,
            architect_enabled=True,
            warm_on_send=True,
            ollama_num_ctx_cap=cfg.profile_quality_num_ctx,
            normalize_max_tokens=384,
            allow_parallel_normalize=False,
        )
    return PerformanceProfile(
        name=PerformanceProfileName.BALANCED,
        label="Balanced",
        summary="3B-class model (not 7B). Best default for CPU chat + light normalization.",
        ollama_model=cfg.ollama_model_balanced,
        max_tokens=cfg.profile_balanced_max_tokens,
        max_tokens_cap=cfg.profile_balanced_max_tokens_cap,
        num_ctx=cfg.profile_balanced_num_ctx,
        max_history_turns=cfg.profile_balanced_max_history,
        timeout_sec=cfg.profile_balanced_timeout_sec,
        temperature=cfg.profile_balanced_temperature,
        system_prompt_relpath=cfg.profile_balanced_system_prompt_file,
        batch_concurrency=cfg.local_llm_batch_concurrency,
        architect_max_phases=min(3, cfg.architect_max_phases),
        architect_enabled=True,
        warm_on_send=True,
        ollama_num_ctx_cap=cfg.profile_balanced_num_ctx,
        normalize_max_tokens=320,
        allow_parallel_normalize=False,
    )


def get_performance_profile(name: str | PerformanceProfileName | None = None) -> PerformanceProfile:
    cfg = get_settings()
    parsed = name if isinstance(name, PerformanceProfileName) else parse_performance_profile(
        name if isinstance(name, str) else cfg.local_llm_performance_profile
    )
    return _profile(parsed, cfg)


def load_system_prompt_for_profile(profile: PerformanceProfile) -> str:
    try:
        return load_prompt_file(profile.system_prompt_relpath)
    except FileNotFoundError:
        if profile.name == PerformanceProfileName.FAST:
            return (
                "You are a concise assistant for a sports arbitrage Python project. "
                "Answer briefly in bullets."
            )
        from prompt_loader import get_default_system_prompt

        return get_default_system_prompt()


def profile_markdown(profile: PerformanceProfile) -> str:
    arch = (
        f"enabled (max {profile.architect_max_phases} phases)"
        if profile.architect_enabled
        else "disabled (switch to Balanced or Quality)"
    )
    return (
        f"**Performance profile:** {profile.label} — {profile.summary}\n\n"
        f"- Model: `{profile.ollama_model}`\n"
        f"- Max tokens: **{profile.max_tokens}** (cap {profile.max_tokens_cap})\n"
        f"- Context: **{profile.num_ctx}** · history: **{profile.max_history_turns}** turns\n"
        f"- Timeout: **{int(profile.timeout_sec)}s** · batch concurrency: **{profile.batch_concurrency}**\n"
        f"- Architect: {arch}\n"
        f"- System prompt: `{profile.system_prompt_relpath}`\n"
        f"- Ollama workloads are **serialized** (one request at a time) to avoid CPU contention."
    )


# Backward compatibility for chat_modes imports
def parse_chat_mode(value: str | None) -> PerformanceProfileName:
    if value and value.strip().lower() in ("fast",):
        return PerformanceProfileName.FAST
    if value and value.strip().lower() in ("quality",):
        return PerformanceProfileName.QUALITY
    if value and value.strip().lower() in ("normal",):
        return PerformanceProfileName.BALANCED
    return parse_performance_profile(value)


def get_chat_profile(mode: str | PerformanceProfileName | None = None) -> PerformanceProfile:
    return get_performance_profile(mode)


def mode_markdown(profile: PerformanceProfile) -> str:
    return profile_markdown(profile)


def activate_performance_profile(name: str | PerformanceProfileName) -> PerformanceProfile:
    """Set active profile for this process (updates env + reloads settings)."""
    import os

    from config import reload_settings

    parsed = name if isinstance(name, PerformanceProfileName) else parse_performance_profile(name)
    os.environ["LOCAL_LLM_PERFORMANCE_PROFILE"] = parsed.value
    reload_settings()
    return get_performance_profile(parsed)


def chat_timeout_help(profile: PerformanceProfile, *, elapsed_sec: int | None = None) -> str:
    """Actionable recovery text after chat timeout (CPU / wrong profile)."""
    cfg = get_settings()
    balanced = cfg.ollama_model_balanced
    fast = cfg.ollama_model_fast
    elapsed = elapsed_sec if elapsed_sec is not None else int(profile.timeout_sec)
    if profile.name == PerformanceProfileName.QUALITY:
        return (
            f"\n\n❌ Timed out after {elapsed}s ({profile.label} — 7B on CPU is too slow for chat).\n\n"
            f"**Switch to Balanced (recommended):**\n"
            f"1. In the UI, select **⚖️ Balanced**\n"
            f"2. Or run: `python scripts/set_profile.py balanced`\n"
            f"3. Pull model: `ollama pull {balanced}`\n\n"
            f"**Faster:** **⚡ Fast** + `ollama pull {fast}`\n\n"
            f"Quality is for Architect/long jobs — not normal chat on CPU."
        )
    if profile.name == PerformanceProfileName.BALANCED:
        return (
            f"\n\n❌ Timed out after {elapsed}s ({profile.label}).\n"
            f"Try **⚡ Fast** profile or: `ollama pull {fast}`\n"
            f"Keep prompts short; close other heavy apps."
        )
    return (
        f"\n\n❌ Timed out after {elapsed}s ({profile.label}).\n"
        f"Try a shorter prompt or switch to **⚖️ Balanced**: `ollama pull {balanced}`"
    )


def pick_fast_ollama_model(requested: str, installed: list[str]) -> str:
    """Prefer configured fast model, then smallest quantised model on disk."""
    from ollama_connect import model_is_installed, pick_ollama_model

    if not installed:
        return requested
    if model_is_installed(requested, installed):
        return pick_ollama_model(requested, installed)
    for hint in ("1.5b", "1b", "2b", "3b", "small"):
        for name in installed:
            if hint in name.lower():
                return name
    return pick_ollama_model(requested, installed)
