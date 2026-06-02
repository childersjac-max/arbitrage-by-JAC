"""Persist web UI settings and chat history between sessions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from chat_modes import get_chat_profile, parse_chat_mode
from config import get_settings
from paths import PACKAGE_DIR
DATA_DIR = PACKAGE_DIR / "data"
UI_STATE_FILE = DATA_DIR / "ui_state.json"
CHAT_HISTORY_FILE = DATA_DIR / "chat_history.json"

DEFAULT_REFERENCE = {
    "nba_cha": "Charlotte Hornets",
    "nba_lal": "Los Angeles Lakers",
    "nba_bos": "Boston Celtics",
}


def _default_ui_state() -> dict[str, Any]:
    cfg = get_settings()
    mode = parse_chat_mode(cfg.local_llm_default_chat_mode)
    profile = get_chat_profile(mode)
    return {
        "chat_mode": mode.value,
        "temperature": float(profile.temperature),
        "max_tokens": int(profile.max_tokens),
        "reference_json": json.dumps(DEFAULT_REFERENCE, indent=2),
        "fragments_text": "",
    }


def load_ui_state() -> dict[str, Any]:
    if not UI_STATE_FILE.is_file():
        return _default_ui_state()
    try:
        data = json.loads(UI_STATE_FILE.read_text(encoding="utf-8"))
        base = _default_ui_state()
        base.update({k: data[k] for k in base if k in data})
        profile = get_chat_profile(parse_chat_mode(str(base.get("chat_mode", "fast"))))
        if int(base.get("max_tokens", profile.max_tokens)) > profile.max_tokens_cap:
            base["max_tokens"] = profile.max_tokens_cap
        return base
    except (json.JSONDecodeError, OSError):
        return _default_ui_state()


def save_ui_state(
    *,
    chat_mode: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    reference_json: str | None = None,
    fragments_text: str | None = None,
) -> None:
    state = load_ui_state()
    if chat_mode is not None:
        state["chat_mode"] = parse_chat_mode(chat_mode).value
    if temperature is not None:
        state["temperature"] = float(temperature)
    if max_tokens is not None:
        state["max_tokens"] = int(max_tokens)
    if reference_json is not None:
        state["reference_json"] = reference_json
    if fragments_text is not None:
        state["fragments_text"] = fragments_text
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UI_STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def load_chat_history() -> list[list[str | None]]:
    if not CHAT_HISTORY_FILE.is_file():
        return []
    try:
        data = json.loads(CHAT_HISTORY_FILE.read_text(encoding="utf-8"))
        messages = data.get("messages", [])
        if not isinstance(messages, list):
            return []
        return [[str(p[0]) if len(p) > 0 and p[0] is not None else None,
                   str(p[1]) if len(p) > 1 and p[1] is not None else None] for p in messages]
    except (json.JSONDecodeError, OSError, TypeError, IndexError):
        return []


def save_chat_history(history: list[list[str | None]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "messages": history,
    }
    CHAT_HISTORY_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def clear_chat_history() -> None:
    save_chat_history([])
