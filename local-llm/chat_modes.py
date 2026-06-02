"""Fast vs normal chat profiles for CPU/GPU-friendly Ollama use."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from config import LocalLLMSettings, get_settings
from prompt_loader import load_prompt_file


class ChatMode(str, Enum):
    FAST = "fast"
    NORMAL = "normal"


@dataclass(frozen=True)
class ChatModeProfile:
    mode: ChatMode
    label: str
    summary: str
    ollama_model: str
    max_tokens: int
    max_tokens_cap: int
    num_ctx: int
    max_history_turns: int
    timeout_sec: float
    system_prompt_relpath: str
    temperature: float
    warm_on_send: bool


def _profile_from_settings(mode: ChatMode, cfg: LocalLLMSettings) -> ChatModeProfile:
    if mode == ChatMode.FAST:
        return ChatModeProfile(
            mode=mode,
            label="Fast (CPU)",
            summary=(
                "Small context, short system prompt, fewer history turns. "
                "Uses `OLLAMA_MODEL_FAST` (falls back to smallest installed model)."
            ),
            ollama_model=cfg.ollama_model_fast,
            max_tokens=cfg.local_llm_fast_max_tokens,
            max_tokens_cap=cfg.local_llm_fast_max_tokens_cap,
            num_ctx=cfg.local_llm_fast_num_ctx,
            max_history_turns=cfg.local_llm_fast_max_history,
            timeout_sec=cfg.local_llm_fast_timeout_sec,
            system_prompt_relpath=cfg.local_llm_fast_system_prompt_file,
            temperature=cfg.local_llm_fast_temperature,
            warm_on_send=True,
        )
    return ChatModeProfile(
        mode=mode,
        label="Normal",
        summary=(
            "Full arbitrage architect system prompt and larger context. "
            "Uses `OLLAMA_MODEL` from `.env`."
        ),
        ollama_model=cfg.ollama_model,
        max_tokens=cfg.local_llm_normal_max_tokens,
        max_tokens_cap=cfg.local_llm_normal_max_tokens_cap,
        num_ctx=cfg.local_llm_normal_num_ctx,
        max_history_turns=cfg.local_llm_normal_max_history,
        timeout_sec=cfg.local_llm_normal_timeout_sec,
        system_prompt_relpath=cfg.local_llm_normal_system_prompt_file,
        temperature=cfg.local_llm_normal_temperature,
        warm_on_send=True,
    )


def parse_chat_mode(value: str | None) -> ChatMode:
    if value and value.strip().lower() == ChatMode.FAST.value:
        return ChatMode.FAST
    return ChatMode.NORMAL


def get_chat_profile(mode: str | ChatMode | None = None) -> ChatModeProfile:
    parsed = mode if isinstance(mode, ChatMode) else parse_chat_mode(
        mode if isinstance(mode, str) else None
    )
    return _profile_from_settings(parsed, get_settings())


def load_system_prompt_for_profile(profile: ChatModeProfile) -> str:
    try:
        return load_prompt_file(profile.system_prompt_relpath)
    except FileNotFoundError:
        if profile.mode == ChatMode.FAST:
            return (
                "You are a concise assistant for a sports arbitrage Python project. "
                "Answer briefly and technically. Prefer short bullet points."
            )
        from prompt_loader import get_default_system_prompt

        return get_default_system_prompt()


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


def mode_markdown(profile: ChatModeProfile) -> str:
    return (
        f"**Mode:** {profile.label} — {profile.summary}\n\n"
        f"- Model: `{profile.ollama_model}`\n"
        f"- Max tokens: **{profile.max_tokens}** (cap {profile.max_tokens_cap})\n"
        f"- Context: **{profile.num_ctx}** tokens · history: **{profile.max_history_turns}** turns\n"
        f"- Timeout: **{int(profile.timeout_sec)}s**\n"
        f"- System prompt: `{profile.system_prompt_relpath}`"
    )
