#!/usr/bin/env python3
"""
Local web UI for your private LLM (Ollama).

Run:
  pip install -r requirements-app.txt
  python web_app.py

Then open http://127.0.0.1:7860 in your browser.

Settings and chat history persist in local-llm/data/ between restarts.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

try:
    import gradio as gr
except ModuleNotFoundError:
    print(
        "\nERROR: Gradio is not installed in this Python environment.\n\n"
        "From the local-llm folder, run ONE of:\n\n"
        "  Git Bash:\n"
        "    bash scripts/setup.sh\n"
        "    source .venv/Scripts/activate\n"
        "    python web_app.py\n\n"
        "  Windows CMD:\n"
        "    scripts\\setup.bat\n"
        "    scripts\\run_app.bat\n\n"
        "  Or without venv:\n"
        "    pip install -r requirements.txt -r requirements-app.txt\n"
        "    python web_app.py\n",
        file=sys.stderr,
    )
    raise SystemExit(1) from None

from performance_profiles import get_performance_profile, load_system_prompt_for_profile
from config import get_settings, reload_settings
from local_inference import LocalInferenceClient
from ollama_connect import (
    check_ollama_reachable,
    format_connection_help,
    get_effective_ollama_model,
    ollama_chat_completion,
    ollama_chat_stream,
    prefer_buffered_transport,
    warmup_ollama,
    warmup_ollama_model,
)
from paths import ENV_FILE, ENV_EXAMPLE, PACKAGE_DIR, ensure_env_file
from prompt_loader import get_default_system_prompt, get_system_prompt_info, system_prompt_path
from prompt_types import ChatMessage
from architect_output import (
    default_mega_prompt_path,
    load_mega_prompt_file,
    save_architect_result,
    save_mega_prompt_file,
)
from architect_pipeline import run_architect
from ui.chat_helpers import (
    build_chat_api_messages,
    clamp_ui_max_tokens,
    reveal_text_chunks,
    settings_source_markdown,
)
from ui.chat_tab import load_messages_from_disk, mount_copilot_chat_tab
from ui.copilot_styles import COPILOT_CSS, copilot_theme, render_header_html
from ui_state import (
    clear_chat_history,
    load_chat_history,
    load_ui_state,
    save_chat_history,
    save_ui_state,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if Path.cwd().resolve() != PACKAGE_DIR.resolve():
    print(
        f"Note: run from the local-llm folder.\n"
        f"  cd {PACKAGE_DIR}\n"
        f"  python web_app.py\n"
        f"(You started in {Path.cwd()})"
    )
os.chdir(PACKAGE_DIR)
# Prevent corporate/VPN proxies from breaking localhost (curl works, Python httpx often didn't).
_no = os.environ.get("NO_PROXY", "")
_extra = "127.0.0.1,localhost,127.0.0.1:11434"
os.environ["NO_PROXY"] = ",".join(filter(None, {_no, _extra} if _no else {_extra}))
if not ENV_FILE.is_file() and ENV_EXAMPLE.is_file():
    ensure_env_file()
    print(f"Created {ENV_FILE} from .env.example — set OLLAMA_MODEL to a model from `ollama list`.")
reload_settings()

_SAVED = load_ui_state()
_INITIAL_PROFILE_NAME = str(
    _SAVED.get("performance_profile", get_settings().local_llm_performance_profile)
)
_INITIAL_PROFILE = get_performance_profile(_INITIAL_PROFILE_NAME)


# Backward-compatible aliases for tests/imports
_build_chat_api_messages = build_chat_api_messages
_clamp_ui_max_tokens = clamp_ui_max_tokens
_reveal_text_chunks = reveal_text_chunks
_settings_source_markdown = settings_source_markdown


def _status_markdown() -> str:
    cfg = get_settings()
    prof = get_performance_profile()
    env_line = f"✅ `{ENV_FILE}`" if ENV_FILE.is_file() else f"⚠️ missing `{ENV_FILE}`"
    return (
        f"**Backend:** `{cfg.local_llm_backend.value}` · "
        f"**Profile:** `{prof.name.value}` · **Model:** `{prof.ollama_model}` · "
        f"**Ollama:** `{cfg.ollama_host}` · {env_line}"
    )


async def check_connection() -> str:
    ok, msg = await check_ollama_reachable()
    if ok:
        return f"✅ Connected to Ollama.\n\n{_status_markdown()}"
    return f"❌ {msg}"


async def chat_respond(
    message: str,
    history: list[list[str | None]] | None,
    system_prompt: str,
    temperature: float,
    max_tokens: int,
) -> str:
    if not message or not message.strip():
        return ""

    messages: list[ChatMessage] = []
    sys_text = (system_prompt or "").strip()
    if sys_text:
        messages.append(ChatMessage("system", sys_text))

    for pair in history or []:
        if not pair:
            continue
        user_text = pair[0] if len(pair) > 0 else None
        bot_text = pair[1] if len(pair) > 1 else None
        if user_text:
            messages.append(ChatMessage("user", str(user_text)))
        if bot_text:
            messages.append(ChatMessage("assistant", str(bot_text)))

    messages.append(ChatMessage("user", message.strip()))

    ok, preflight = await check_ollama_reachable()
    if not ok:
        return f"❌ {preflight}"

    try:
        async with LocalInferenceClient() as client:
            result = await client.chat(
                messages,
                temperature=temperature,
                max_tokens=int(max_tokens),
            )
            text = (result.content or "").strip()
            if not text:
                return (
                    "⚠️ Ollama returned an empty reply. "
                    "Lower **Max tokens**, shorten the system prompt, or check the model with "
                    "`ollama run <model>` in a terminal."
                )
            return text
    except ConnectionError as exc:
        return str(exc)
    except Exception as exc:
        logger.exception("chat failed")
        return format_connection_help(exc)


async def normalize_names(
    fragments_text: str,
    reference_json: str,
) -> tuple[str, str]:
    save_ui_state(fragments_text=fragments_text, reference_json=reference_json)

    fragments = [ln.strip() for ln in fragments_text.splitlines() if ln.strip()]
    if not fragments:
        return "", "⚠️ Add at least one raw name (one per line)."

    try:
        reference = json.loads(reference_json)
        if not isinstance(reference, dict):
            raise ValueError("Reference must be a JSON object")
        reference = {str(k): str(v) for k, v in reference.items()}
    except json.JSONDecodeError as exc:
        return "", f"⚠️ Invalid reference JSON: {exc}"

    try:
        async with LocalInferenceClient() as client:
            result = await client.normalize_batch(fragments, reference)
        pretty = json.dumps(result.mapping, indent=2, ensure_ascii=False)
        meta = (
            f"✅ Done in {result.latency_ms:.0f} ms · "
            f"attempts={result.attempts} · model={get_settings().ollama_model}"
        )
        return pretty, meta
    except ConnectionError as exc:
        return "", str(exc)
    except Exception as exc:
        logger.exception("normalize failed")
        return "", format_connection_help(exc)


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Local Copilot") as demo:
        with gr.Accordion("Connection & diagnostics", open=False):
            status_md = gr.Markdown(_status_markdown())
            with gr.Row():
                health_btn = gr.Button("Check Ollama", variant="secondary", size="sm")
                warmup_btn = gr.Button("Wake up model", variant="secondary", size="sm")
                refresh_btn = gr.Button("Reload config", variant="secondary", size="sm")
            health_out = gr.Markdown("Expand to check Ollama status.")

        with gr.Tabs():
            with gr.Tab("Chat"):
                chat_refs = mount_copilot_chat_tab(_SAVED, _INITIAL_PROFILE)

            with gr.Tab("🏗️ Architect (8B)"):
                _mega_path = str(default_mega_prompt_path())
                gr.Markdown(
                    f"""
### Easy mode (3 steps)
1. **Open Ollama** (Start menu) — leave it running  
2. **Edit your prompt** — button below opens `prompts/mega_prompt.txt` in Notepad (or edit the big box)  
3. **Click the green button** — wait 5–15 min — results auto-save to **`harvester/generated/`**

*Easiest of all:* double-click **`scripts/run_architect_easy.bat`** in File Explorer (no browser).
"""
                )
                with gr.Row():
                    open_notepad_btn = gr.Button("📝 Open prompt file (Notepad)", variant="secondary")
                    reload_file_btn = gr.Button("↻ Reload my prompt file", variant="secondary")
                    save_file_btn = gr.Button("💾 Save box → prompt file", variant="secondary")
                mega_in = gr.Textbox(
                    label="Your big prompt (same as mega_prompt.txt)",
                    lines=14,
                    value=load_mega_prompt_file(),
                )
                arch_phases = gr.Slider(
                    2,
                    8,
                    value=int(get_settings().architect_max_phases),
                    step=1,
                    label="How many build steps? (start with 5)",
                )
                auto_save = gr.Checkbox(
                    value=True,
                    label="Automatically save results to harvester/generated/ (recommended)",
                )
                arch_run = gr.Button("▶ START — Run my big prompt", variant="primary", size="lg")
                arch_status = gr.Markdown("Ready. Click **START** when Ollama is open.")
                arch_plan = gr.Code(label="Plan JSON", language="json")
                arch_output = gr.Textbox(
                    label="Preview (full files are on disk after run)",
                    lines=12,
                    max_lines=40,
                )
                arch_folder = gr.Textbox(
                    label="Saved folder (open in File Explorer)",
                    interactive=False,
                )

                def open_prompt_hint() -> str:
                    path = default_mega_prompt_path()
                    return (
                        f"**Notepad:** edit and save `{path}` then click **Reload my prompt file**.\n\n"
                        f"Or run: `notepad \"{path}\"`"
                    )

                open_notepad_btn.click(
                    open_prompt_hint,
                    outputs=[arch_status],
                )
                reload_file_btn.click(
                    lambda: load_mega_prompt_file(),
                    outputs=[mega_in],
                )

                def save_box_to_file(text: str) -> str:
                    path = save_mega_prompt_file(text)
                    return f"✅ Saved to `{path}`"

                save_file_btn.click(save_box_to_file, inputs=[mega_in], outputs=[arch_status])

                async def run_architect_ui(
                    mega: str,
                    n_phases: float,
                    do_save: bool,
                ):
                    prof = get_performance_profile()
                    if not prof.architect_enabled:
                        yield (
                            "⚠️ Architect is **disabled** in **Fast** profile. "
                            "Switch to **Balanced** or **Quality**, or run: "
                            "`python scripts/set_profile.py balanced`",
                            "{}",
                            "",
                            "",
                        )
                        return
                    if not (mega or "").strip():
                        yield "⚠️ Write a prompt first (or click Reload my prompt file).", "{}", "", ""
                        return
                    yield "⏳ Connecting to Ollama…", "{}", "", ""
                    ok, warm = await warmup_ollama()
                    if not ok:
                        yield f"❌ {warm}", "{}", "", ""
                        return
                    yield f"✅ {warm}\n\n⏳ Running architect — **do not close Git Bash**. This takes several minutes.", "{}", "", ""

                    logs: list[str] = []

                    def progress(msg: str) -> None:
                        logs.append(msg)

                    try:
                        save_mega_prompt_file(mega)
                        phases = int(n_phases)
                        if prof.architect_max_phases > 0:
                            phases = min(phases, prof.architect_max_phases)
                        result = await run_architect(
                            mega,
                            max_phases=phases,
                            on_progress=progress,
                        )
                    except Exception as exc:
                        yield f"❌ {exc}", "{}", "", ""
                        return

                    plan_str = json.dumps(result.plan_json, indent=2)
                    preview_parts = [f"=== PLAN ===\n{plan_str}\n"]
                    for p in result.phases:
                        preview_parts.append(
                            f"\n\n=== PHASE {p.step}: {p.title} ===\n{p.content[:2000]}..."
                            if len(p.content) > 2000
                            else f"\n\n=== PHASE {p.step}: {p.title} ===\n{p.content}"
                        )
                    total_ms = sum(p.latency_ms for p in result.phases)
                    folder_line = ""
                    out_dir_str = ""
                    if do_save:
                        saved = save_architect_result(result)
                        out_dir_str = str(saved)
                        folder_line = f"\n\n📁 **Open this folder:** `{saved}`"
                    log_text = "\n".join(f"- {x}" for x in logs)
                    status = (
                        f"✅ **Finished** — {len(result.phases)} phase(s) in ~{total_ms/1000:.1f}s\n\n"
                        f"{log_text}{folder_line}\n\n"
                        "In File Explorer go to `harvester` → `generated` → newest date folder. "
                        "Read `README.txt` first."
                    )
                    yield status, plan_str, "".join(preview_parts), out_dir_str

                arch_run.click(
                    run_architect_ui,
                    inputs=[mega_in, arch_phases, auto_save],
                    outputs=[arch_status, arch_plan, arch_output, arch_folder],
                )

            with gr.Tab("🏷️ Normalize names"):
                gr.Markdown("Inputs are saved automatically when you click Normalize.")
                with gr.Row():
                    with gr.Column():
                        fragments_text = gr.Textbox(
                            label="Raw names (one per line)",
                            lines=10,
                            value=_SAVED.get("fragments_text", ""),
                            placeholder="CHA Hornets\nCharlotte\nLakers -3.5",
                        )
                        reference_json = gr.Textbox(
                            label="Reference JSON (id → official name)",
                            lines=8,
                            value=_SAVED.get("reference_json", "{}"),
                        )
                        norm_btn = gr.Button("Normalize", variant="primary")
                    with gr.Column():
                        norm_out = gr.Code(label="Result JSON", language="json")
                        norm_meta = gr.Markdown()

                norm_btn.click(
                    normalize_names,
                    inputs=[fragments_text, reference_json],
                    outputs=[norm_out, norm_meta],
                )

        async def reload_ollama_only() -> str:
            reload_settings()
            return await check_connection()

        async def wake_ollama() -> str:
            ok, msg = await warmup_ollama(load_model=True)
            return f"✅ {msg}" if ok else f"❌ {msg}"

        health_btn.click(check_connection, outputs=health_out)
        warmup_btn.click(wake_ollama, outputs=health_out)
        refresh_btn.click(reload_ollama_only, outputs=health_out)

        async def on_page_load() -> tuple[str, list, str, str, float, float, str, str]:
            ok, warm_msg = await warmup_ollama(load_model=False)
            if ok:
                health = f"✅ {warm_msg}\n\n{_status_markdown()}"
            else:
                health = f"❌ {warm_msg}"
            state = load_ui_state()
            prof_name = str(
                state.get("performance_profile", get_settings().local_llm_performance_profile)
            )
            prof = get_performance_profile(prof_name)
            return (
                health,
                load_messages_from_disk(),
                settings_source_markdown(prof_name),
                load_system_prompt_for_profile(prof),
                float(state["temperature"]),
                float(state["max_tokens"]),
                f"**Profile:** {prof.label} · **Model:** `{prof.ollama_model}`",
                render_header_html(prof, ollama_ok=ok),
            )

        demo.load(
            on_page_load,
            outputs=[
                health_out,
                chat_refs.chatbot,
                chat_refs.system_prompt_source,
                chat_refs.system_prompt,
                chat_refs.temperature,
                chat_refs.max_tokens,
                chat_refs.status_bar,
                chat_refs.header_html,
            ],
        )

        gr.Markdown(
            "---\n"
            f"**System prompt file:** `{system_prompt_path()}` · "
            f"**Saved files:** `data/ui_state.json` · `data/chat_history.json` · "
            f"Port `{get_settings().local_llm_ui_host}:{get_settings().local_llm_ui_port}`"
        )

    return demo


def _open_browser_when_ready(url: str, delay_sec: float = 2.0) -> None:
    time.sleep(delay_sec)
    webbrowser.open(url)


def main() -> None:
    cfg = get_settings()
    host = cfg.local_llm_ui_host
    port = cfg.local_llm_ui_port
    url = f"http://{host}:{port}"

    print("=" * 60)
    print("  LOCAL LLM CHAT (Ollama + Gradio)")
    print(f"  Folder: {PACKAGE_DIR}")
    print(f"  Open:   {url}")
    prof = get_performance_profile()
    print(f"  Profile: {prof.name.value} · Model: {prof.ollama_model}")
    print(f"  Switch:  python scripts/set_profile.py fast|balanced|quality")
    print("  NOT the harvester dashboard (that is harvester/web_app.py :8765)")
    print("=" * 60)

    threading.Thread(
        target=_open_browser_when_ready,
        args=(url,),
        daemon=True,
    ).start()

    demo = build_ui()
    demo.queue(default_concurrency_limit=1)
    print(f"\n>>> Open in your browser: {url}\n")
    print(f">>> Settings: {PACKAGE_DIR / 'data' / 'ui_state.json'}\n")
    demo.launch(
        server_name=host,
        server_port=port,
        share=False,
        show_error=True,
        inbrowser=False,
        theme=copilot_theme(),
        css=COPILOT_CSS,
    )


if __name__ == "__main__":
    main()
