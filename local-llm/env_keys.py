"""Update keys in local-llm/.env without disturbing other settings."""

from __future__ import annotations

import re
from pathlib import Path


def upsert_env_keys(env_path: Path, example: Path, updates: dict[str, str]) -> None:
    if env_path.is_file():
        text = env_path.read_text(encoding="utf-8")
    elif example.is_file():
        text = example.read_text(encoding="utf-8")
    else:
        text = ""

    for key, value in updates.items():
        line = f"{key}={value}\n"
        if re.search(rf"^{re.escape(key)}=", text, flags=re.MULTILINE):
            text = re.sub(rf"^{re.escape(key)}=.*$", line.strip(), text, flags=re.MULTILINE)
        else:
            text = text.rstrip() + "\n" + line

    env_path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
