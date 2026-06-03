"""Remote (away from home Wi-Fi) access helpers for the Gradio UI."""

from __future__ import annotations

import secrets
import sys
from pathlib import Path

from env_keys import upsert_env_keys


def resolve_gradio_auth(user: str | None, password: str | None) -> tuple[str, str] | None:
    u = (user or "").strip()
    p = password or ""
    if u and p:
        return (u, p)
    return None


def validate_share_mode(*, share: bool, auth: tuple[str, str] | None, insecure: bool) -> None:
    if not share:
        return
    if auth:
        return
    if insecure:
        print(
            "\nWARNING: LOCAL_LLM_UI_SHARE=1 without a password. "
            "Anyone with the gradio.live link can use your PC's LLM.\n"
        )
        return
    print(
        "\nERROR: Remote share mode requires a login password.\n\n"
        "  Run once:\n"
        "    python scripts/enable_remote.py\n\n"
        "  Or set in .env:\n"
        "    LOCAL_LLM_UI_AUTH_USER=yourname\n"
        "    LOCAL_LLM_UI_AUTH_PASSWORD=your-secret\n\n"
        "  Advanced (not recommended): LOCAL_LLM_UI_SHARE_INSECURE=1\n",
        file=sys.stderr,
    )
    raise SystemExit(1)


def _read_env_value(env_path: Path, key: str) -> str:
    if not env_path.is_file():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return ""


def ensure_remote_credentials(
    env_path: Path,
    example: Path,
    *,
    user: str = "admin",
    password: str | None = None,
    only_if_missing: bool = False,
) -> tuple[str, str]:
    """Write share=1 and auth credentials to .env; generate password if omitted."""
    existing_user = _read_env_value(env_path, "LOCAL_LLM_UI_AUTH_USER")
    existing_pwd = _read_env_value(env_path, "LOCAL_LLM_UI_AUTH_PASSWORD")
    if only_if_missing and existing_user and existing_pwd:
        upsert_env_keys(env_path, example, {"LOCAL_LLM_UI_SHARE": "1"})
        return existing_user, existing_pwd

    pwd = password or existing_pwd or secrets.token_urlsafe(12)
    final_user = user if password or not existing_user else existing_user
    upsert_env_keys(
        env_path,
        example,
        {
            "LOCAL_LLM_UI_SHARE": "1",
            "LOCAL_LLM_UI_AUTH_USER": final_user,
            "LOCAL_LLM_UI_AUTH_PASSWORD": pwd,
        },
    )
    return final_user, pwd


def save_public_url(package_dir: Path, url: str) -> Path:
    path = package_dir / "data" / "remote_url.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(url.strip() + "\n", encoding="utf-8")
    return path
