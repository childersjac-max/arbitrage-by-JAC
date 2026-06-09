"""Convert between Gradio message format and legacy tuple history on disk."""

from __future__ import annotations

THINKING_PREFIXES = ("⏳", "●", "…")


def is_placeholder_content(text: str | None) -> bool:
    if not text:
        return False
    s = str(text).strip()
    return s.startswith(THINKING_PREFIXES) or s.startswith("❌") and "Timed out" in s


def tuples_to_messages(history: list[list[str | None]] | None) -> list[dict[str, str]]:
    """Legacy [[user, bot], ...] → OpenAI-style messages for Gradio Chatbot."""
    out: list[dict[str, str]] = []
    for pair in history or []:
        if not pair:
            continue
        user = pair[0] if len(pair) > 0 else None
        bot = pair[1] if len(pair) > 1 else None
        if user:
            out.append({"role": "user", "content": str(user)})
        if bot is not None and str(bot).strip():
            out.append({"role": "assistant", "content": str(bot)})
    return out


def messages_to_tuples(messages: list[dict[str, str]] | None) -> list[list[str | None]]:
    """Persist as legacy pairs for ui_state compatibility."""
    pairs: list[list[str | None]] = []
    pending_user: str | None = None
    for msg in messages or []:
        role = str(msg.get("role", ""))
        content = str(msg.get("content", ""))
        if role == "user":
            if pending_user is not None:
                pairs.append([pending_user, None])
            pending_user = content
        elif role == "assistant":
            if pending_user is None:
                pairs.append([None, content])
            else:
                pairs.append([pending_user, content])
                pending_user = None
    if pending_user is not None:
        pairs.append([pending_user, None])
    return pairs


def last_user_message(messages: list[dict[str, str]]) -> str | None:
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return str(msg.get("content", ""))
    return None


def strip_trailing_assistant(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    out = list(messages)
    while out and out[-1].get("role") == "assistant":
        out.pop()
    return out


def append_turn(
    messages: list[dict[str, str]],
    user: str,
    assistant: str,
) -> list[dict[str, str]]:
    out = list(messages)
    out.append({"role": "user", "content": user})
    out.append({"role": "assistant", "content": assistant})
    return out


def set_last_assistant(messages: list[dict[str, str]], content: str) -> list[dict[str, str]]:
    out = list(messages)
    if out and out[-1].get("role") == "assistant":
        out[-1] = {"role": "assistant", "content": content}
    else:
        out.append({"role": "assistant", "content": content})
    return out
