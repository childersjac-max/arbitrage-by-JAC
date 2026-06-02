#!/usr/bin/env python3
"""Diagnose local-llm + Ollama setup (run from local-llm/)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
os.chdir(PACKAGE_DIR)
sys.path.insert(0, str(PACKAGE_DIR))

_no = os.environ.get("NO_PROXY", "")
_extra = "127.0.0.1,localhost,127.0.0.1:11434"
os.environ["NO_PROXY"] = ",".join(filter(None, {_no, _extra} if _no else {_extra}))

from config import get_settings  # noqa: E402
from ollama_connect import check_ollama_reachable, get_effective_ollama_model  # noqa: E402
from paths import ENV_FILE, ENV_EXAMPLE, ensure_env_file  # noqa: E402
from prompt_loader import get_default_system_prompt  # noqa: E402


async def main() -> int:
    print("local-llm doctor")
    print(f"  folder: {PACKAGE_DIR}")
    if not ENV_FILE.is_file():
        if ENV_EXAMPLE.is_file():
            ensure_env_file()
            print(f"  created: {ENV_FILE} (from .env.example)")
        else:
            print(f"  warn: no {ENV_FILE} — using defaults")
    else:
        print(f"  config:  {ENV_FILE}")

    cfg = get_settings()
    print(f"  backend: {cfg.local_llm_backend.value}")
    print(f"  host:    {cfg.ollama_host}")
    from performance_profiles import get_performance_profile, profile_markdown

    prof = get_performance_profile()
    print(profile_markdown(prof).replace("**", ""))
    print(f"  models: fast={cfg.ollama_model_fast} balanced={cfg.ollama_model_balanced} quality={cfg.ollama_model_quality}")
    print(f"  ui:      http://{cfg.local_llm_ui_host}:{cfg.local_llm_ui_port}")

    from performance_profiles import load_system_prompt_for_profile

    sp = load_system_prompt_for_profile(prof)
    print(f"  system prompt: {len(sp)} chars from {prof.system_prompt_relpath}")

    ok, msg = await check_ollama_reachable()
    if ok:
        print(f"  ollama:  OK — {msg}")
        try:
            effective = await get_effective_ollama_model()
            print(f"  effective model: {effective}")
        except Exception as exc:
            print(f"  effective model: (error) {exc}")
        print("\nNext: python web_app.py  →  http://127.0.0.1:7860")
        return 0

    print(f"  ollama:  FAIL\n{msg}")
    print("\nFix: start Ollama from the Start menu, then: ollama pull <model>")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
