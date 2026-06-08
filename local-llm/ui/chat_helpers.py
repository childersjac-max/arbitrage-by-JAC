"""Shared chat UI helpers (no Gradio dependency)."""

from __future__ import annotations

import asyncio
import time

from performance_profiles import get_performance_profile, profile_markdown


async def reveal_text_chunks(text: str, *, words_per_chunk: int = 3, delay_sec: float = 0.03):
    """Pseudo-streaming when true Ollama stream is unavailable."""
    words = text.split()
    if not words:
        yield text
        return
    buf: list[str] = []
    for i in range(0, len(words), words_per_chunk):
        buf.extend(words[i : i + words_per_chunk])
        yield " ".join(buf)
        await asyncio.sleep(delay_sec)
    yield text


def clamp_ui_max_tokens(value: float, profile) -> int:
    return max(128, min(int(value), profile.max_tokens_cap))


def build_chat_api_messages(
    message: str,
    history: list | None,
    system_prompt: str,
    *,
    max_history_turns: int,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    sys_text = (system_prompt or "").strip()
    if sys_text:
        messages.append({"role": "system", "content": sys_text})
    pairs = [p for p in (history or []) if p][-max_history_turns:]
    for pair in pairs:
        user_text = pair[0] if len(pair) > 0 else None
        bot_text = pair[1] if len(pair) > 1 else None
        if user_text:
            messages.append({"role": "user", "content": str(user_text)})
        if bot_text and not str(bot_text).startswith(("⏳", "●")):
            messages.append({"role": "assistant", "content": str(bot_text)})
    messages.append({"role": "user", "content": message.strip()})
    return messages


def settings_source_markdown(profile_name: str, *, reloaded: bool = False) -> str:
    profile = get_performance_profile(profile_name)
    suffix = " _(reloaded just now)_" if reloaded else ""
    return (
        f"{profile_markdown(profile)}{suffix}\n\n"
        "Tip: switch profile in the bar above or `python scripts/set_profile.py balanced`"
    )
