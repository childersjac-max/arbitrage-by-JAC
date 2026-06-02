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

from chat_modes import (
    ChatMode,
    get_chat_profile,
    load_system_prompt_for_profile,
    mode_markdown,
    parse_chat_mode,
)
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
_INITIAL_MODE = parse_chat_mode(str(_SAVED.get("chat_mode", "fast")))
_INITIAL_PROFILE = get_chat_profile(_INITIAL_MODE)


def _clamp_ui_max_tokens(value: float, profile) -> int:
    return max(128, min(int(value), profile.max_tokens_cap))


def _build_chat_api_messages(
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
        if bot_text and not str(bot_text).startswith("⏳"):
            messages.append({"role": "assistant", "content": str(bot_text)})
    messages.append({"role": "user", "content": message.strip()})
    return messages


def _status_markdown() -> str:
    cfg = get_settings()
    env_line = f"✅ `{ENV_FILE}`" if ENV_FILE.is_file() else f"⚠️ missing `{ENV_FILE}`"
    return (
        f"**Backend:** `{cfg.local_llm_backend.value}` · "
        f"**Model:** `{cfg.ollama_model}` · "
        f"**Ollama:** `{cfg.ollama_host}` · {env_line}"
    )


def _settings_source_markdown(chat_mode: str | None = None, *, reloaded: bool = False) -> str:
    profile = get_chat_profile(chat_mode or str(_SAVED.get("chat_mode", "fast")))
    suffix = " _(reloaded just now)_" if reloaded else ""
    return (
        f"{mode_markdown(profile)}{suffix}\n\n"
        "Edit the system prompt file for this mode, then click **Reload system prompt** "
        "or switch mode and back."
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
    with gr.Blocks(
        title="Private Local LLM",
        theme=gr.themes.Soft(),
    ) as demo:
        gr.Markdown(
            "# Private Local LLM\n"
            "Runs on your machine via Ollama. Settings and chat are saved in `data/`."
        )
        status_md = gr.Markdown(_status_markdown())

        with gr.Row():
            health_btn = gr.Button("Check Ollama connection", variant="secondary")
            warmup_btn = gr.Button("Wake up Ollama", variant="secondary")
            refresh_btn = gr.Button("Reload Ollama / config", variant="secondary")
        health_out = gr.Markdown("Click **Check Ollama connection** before your first message.")

        with gr.Tabs():
            with gr.Tab("💬 Chat"):
                gr.Markdown(
                    "Choose **Fast** for CPU (small model, short prompt) or **Normal** for the full "
                    "arbitrage architect prompt. First reply on CPU can take minutes — a live timer "
                    "is shown while Ollama works."
                )
                chat_mode = gr.Radio(
                    choices=[
                        ("⚡ Fast (CPU)", ChatMode.FAST.value),
                        ("📐 Normal", ChatMode.NORMAL.value),
                    ],
                    value=_INITIAL_MODE.value,
                    label="Chat mode",
                )
                chatbot = gr.Chatbot(height=420, label="Conversation", value=load_chat_history())
                with gr.Accordion("Advanced", open=True):
                    system_prompt_source = gr.Markdown(
                        _settings_source_markdown(_INITIAL_MODE.value)
                    )
                    with gr.Row():
                        load_prompt_btn = gr.Button(
                            "Reload system prompt from file",
                            variant="secondary",
                        )
                        save_settings_btn = gr.Button(
                            "Save current settings as default",
                            variant="secondary",
                        )
                    system_prompt = gr.Textbox(
                        label=f"System prompt ({_INITIAL_PROFILE.system_prompt_relpath})",
                        value=load_system_prompt_for_profile(_INITIAL_PROFILE),
                        lines=14,
                    )
                    with gr.Row():
                        temperature = gr.Slider(
                            0,
                            1.5,
                            value=float(_SAVED["temperature"]),
                            step=0.1,
                            label="Temperature",
                        )
                        max_tokens = gr.Slider(
                            128,
                            _INITIAL_PROFILE.max_tokens_cap,
                            value=int(_SAVED["max_tokens"]),
                            step=64,
                            label=f"Max tokens (cap {_INITIAL_PROFILE.max_tokens_cap} in this mode)",
                        )
                msg = gr.Textbox(
                    label="Your message",
                    placeholder="Explain sports arbitrage in simple terms…",
                    lines=2,
                )
                with gr.Row():
                    send = gr.Button("Send", variant="primary")
                    clear = gr.Button("Clear chat")

                def persist_settings_only(mode: str, temp: float, max_t: float) -> str:
                    save_ui_state(
                        chat_mode=mode,
                        temperature=temp,
                        max_tokens=int(max_t),
                    )
                    return _settings_source_markdown(mode) + " _(saved just now)_"

                def apply_chat_mode(mode: str) -> tuple[float, dict, str, str]:
                    profile = get_chat_profile(mode)
                    save_ui_state(
                        chat_mode=mode,
                        temperature=profile.temperature,
                        max_tokens=profile.max_tokens,
                    )
                    return (
                        profile.temperature,
                        gr.Slider(
                            minimum=128,
                            maximum=profile.max_tokens_cap,
                            value=profile.max_tokens,
                            step=64,
                            label=f"Max tokens (cap {profile.max_tokens_cap} in this mode)",
                        ),
                        load_system_prompt_for_profile(profile),
                        _settings_source_markdown(mode),
                    )

                async def user_submit(
                    message: str,
                    history: list,
                    mode: str,
                    _sys_p: str,
                    temp: float,
                    max_t: float,
                ):
                    profile = get_chat_profile(mode)
                    sys_from_file = load_system_prompt_for_profile(profile)
                    meta = _settings_source_markdown(mode)
                    history = list(history or [])

                    if not message or not message.strip():
                        yield history, "", meta, sys_from_file
                        return

                    max_t = _clamp_ui_max_tokens(max_t, profile)
                    temp = float(temp)
                    save_ui_state(chat_mode=mode, temperature=temp, max_tokens=max_t)

                    ok, preflight = await check_ollama_reachable()
                    if not ok:
                        history.append([message, f"❌ {preflight}"])
                        save_chat_history(history)
                        yield history, "", meta, sys_from_file
                        return

                    wait_msg = (
                        "⏳ Warming up model (reliable mode)…"
                        if prefer_buffered_transport()
                        else "⏳ Connecting to Ollama…"
                    )
                    history.append([message, wait_msg])
                    yield history, "", meta, sys_from_file

                    api_messages = _build_chat_api_messages(
                        message,
                        history[:-1],
                        sys_from_file,
                        max_history_turns=profile.max_history_turns,
                    )
                    timeout_sec = float(profile.timeout_sec)

                    try:
                        model = await get_effective_ollama_model(
                            requested=profile.ollama_model,
                            fast=profile.mode == ChatMode.FAST,
                        )
                    except Exception as exc:
                        history[-1][1] = format_connection_help(exc)
                        save_chat_history(history)
                        yield history, "", meta, sys_from_file
                        return

                    partial = ""
                    started = time.monotonic()
                    queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()
                    use_buffered = prefer_buffered_transport()

                    async def pump() -> None:
                        try:
                            if use_buffered and profile.warm_on_send:
                                await warmup_ollama_model(model)
                            if use_buffered:
                                text = await ollama_chat_completion(
                                    api_messages,
                                    model=model,
                                    temperature=temp,
                                    max_tokens=max_t,
                                    num_ctx=profile.num_ctx,
                                )
                                if text:
                                    await queue.put(("t", text))
                            else:
                                async for token in ollama_chat_stream(
                                    api_messages,
                                    model=model,
                                    temperature=temp,
                                    max_tokens=max_t,
                                    num_ctx=profile.num_ctx,
                                ):
                                    await queue.put(("t", token))
                        except Exception as exc:
                            if not use_buffered:
                                try:
                                    logger.warning(
                                        "stream failed, falling back to buffered: %s", exc
                                    )
                                    text = await ollama_chat_completion(
                                        api_messages,
                                        model=model,
                                        temperature=temp,
                                        max_tokens=max_t,
                                        num_ctx=profile.num_ctx,
                                    )
                                    if text:
                                        await queue.put(("t", text))
                                except Exception as exc2:
                                    await queue.put(("e", exc2))
                            else:
                                await queue.put(("e", exc))
                        await queue.put(("d", None))

                    task = asyncio.create_task(pump())
                    try:
                        while True:
                            elapsed = time.monotonic() - started
                            if elapsed > timeout_sec:
                                task.cancel()
                                suffix = (
                                    f"\n\n❌ Timed out after {int(elapsed)}s ({profile.label}). "
                                    "Try **Fast** mode, lower max tokens, or: "
                                    f"`ollama run {model}`"
                                )
                                history[-1][1] = (partial or "⏳") + suffix
                                break

                            try:
                                kind, payload = await asyncio.wait_for(queue.get(), timeout=2.0)
                            except asyncio.TimeoutError:
                                if not partial:
                                    mode = "generating" if use_buffered else "loading"
                                    history[-1][1] = (
                                        f"⏳ Ollama {mode}… {int(elapsed)}s "
                                        "(CPU can take 5–15 min first time — do not close this tab)"
                                    )
                                else:
                                    history[-1][1] = partial + f" … ({int(elapsed)}s)"
                                yield history, "", meta, sys_from_file
                                continue

                            if kind == "d":
                                if not partial.strip():
                                    history[-1][1] = (
                                        f"⚠️ Empty reply. Try **Fast** mode or shorten "
                                        f"`{profile.system_prompt_relpath}`."
                                    )
                                else:
                                    history[-1][1] = partial
                                break
                            if kind == "e":
                                exc = payload
                                history[-1][1] = (
                                    str(exc)
                                    if isinstance(exc, ConnectionError)
                                    else format_connection_help(
                                        exc if isinstance(exc, BaseException) else None
                                    )
                                )
                                break
                            partial += str(payload)
                            history[-1][1] = partial
                            yield history, "", meta, sys_from_file
                    finally:
                        if not task.done():
                            task.cancel()

                    save_chat_history(history)
                    yield history, "", meta, sys_from_file

                def clear_chat() -> tuple[list, str, str]:
                    clear_chat_history()
                    return [], "", _settings_source_markdown()

                chat_mode.change(
                    apply_chat_mode,
                    inputs=[chat_mode],
                    outputs=[temperature, max_tokens, system_prompt, system_prompt_source],
                )

                send.click(
                    user_submit,
                    inputs=[msg, chatbot, chat_mode, system_prompt, temperature, max_tokens],
                    outputs=[chatbot, msg, system_prompt_source, system_prompt],
                )
                msg.submit(
                    user_submit,
                    inputs=[msg, chatbot, chat_mode, system_prompt, temperature, max_tokens],
                    outputs=[chatbot, msg, system_prompt_source, system_prompt],
                )
                clear.click(
                    clear_chat,
                    outputs=[chatbot, msg, system_prompt_source],
                )
                save_settings_btn.click(
                    persist_settings_only,
                    inputs=[chat_mode, temperature, max_tokens],
                    outputs=[system_prompt_source],
                )
                for field in (temperature, max_tokens):
                    field.change(
                        persist_settings_only,
                        inputs=[chat_mode, temperature, max_tokens],
                        outputs=[system_prompt_source],
                    )

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
                        result = await run_architect(
                            mega,
                            max_phases=int(n_phases),
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

        def reload_system_prompt_from_file(mode: str) -> tuple[str, str]:
            profile = get_chat_profile(mode)
            text = load_system_prompt_for_profile(profile)
            return text, _settings_source_markdown(mode, reloaded=True)

        async def reload_ollama_only() -> str:
            reload_settings()
            return await check_connection()

        async def wake_ollama() -> str:
            ok, msg = await warmup_ollama(load_model=True)
            return f"✅ {msg}" if ok else f"❌ {msg}"

        health_btn.click(check_connection, outputs=health_out)
        warmup_btn.click(wake_ollama, outputs=health_out)
        refresh_btn.click(reload_ollama_only, outputs=health_out)
        load_prompt_btn.click(
            reload_system_prompt_from_file,
            inputs=[chat_mode],
            outputs=[system_prompt, system_prompt_source],
        )

        async def on_page_load() -> tuple[str, list, str, str, float, float]:
            ok, warm_msg = await warmup_ollama(load_model=False)
            if ok:
                health = f"✅ {warm_msg}\n\n{_status_markdown()}"
            else:
                health = f"❌ {warm_msg}"
            state = load_ui_state()
            history = load_chat_history()
            return (
                health,
                history,
                _settings_source_markdown(),
                get_default_system_prompt(),
                float(state["temperature"]),
                float(state["max_tokens"]),
            )

        demo.load(
            on_page_load,
            outputs=[
                health_out,
                chatbot,
                system_prompt_source,
                system_prompt,
                temperature,
                max_tokens,
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
    print(f"  Model:  {cfg.ollama_model}  (see local-llm/.env)")
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
    )


if __name__ == "__main__":
    main()
