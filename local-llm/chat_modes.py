"""Backward-compatible aliases — use performance_profiles.py."""

from performance_profiles import (
    PerformanceProfile,
    PerformanceProfileName,
    get_chat_profile,
    get_performance_profile,
    load_system_prompt_for_profile,
    mode_markdown,
    parse_chat_mode,
    parse_performance_profile,
    pick_fast_ollama_model,
    profile_markdown,
)

__all__ = [
    "PerformanceProfile",
    "PerformanceProfileName",
    "get_chat_profile",
    "get_performance_profile",
    "load_system_prompt_for_profile",
    "mode_markdown",
    "parse_chat_mode",
    "parse_performance_profile",
    "pick_fast_ollama_model",
    "profile_markdown",
]
