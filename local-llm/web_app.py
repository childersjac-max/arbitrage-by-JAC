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

import json
import logging
import os
import threading
import time
import webbrowser

import gradio as gr

from config import get_settings, reload_settings
from local_inference import LocalInferenceClient
from ollama_connect import (
    check_ollama_reachable,
    format_connection_help,
    resolve_ollama,
    warmup_ollama,
)
from paths import ENV_FILE, PACKAGE_DIR
from prompt_loader import get_system_prompt_info, system_prompt_path
from prompt_types import ChatMessage
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

os.chdir(PACKAGE_DIR)
# Prevent corporate/VPN proxies from breaking localhost (curl works, Python httpx often didn't).
_no = os.environ.get("NO_PROXY", "")
_extra = "127.0.0.1,localhost,127.0.0.1:11434"
os.environ["NO_PROXY"] = ",".join(filter(None, {_no, _extra} if _no else {_extra}))
reload_settings()

_SAVED = load_ui_state()


def _status_markdown() -> str:
    cfg = get_settings()
    env_line = f"✅ `{ENV_FILE}`" if ENV_FILE.is_file() else f"⚠️ missing `{ENV_FILE}`"
    return (
        f"**Backend:** `{cfg.local_llm_backend.value}` · "
        f"**Model:** `{cfg.ollama_model}` · "
        f"**Ollama:** `{cfg.ollama_host}` · {env_line}"
    )


def _settings_source_markdown(from_file: bool = False) -> str:
    if from_file:
        return f"**System prompt:** loaded from `{system_prompt_path()}` and saved as your default."
    return (
        "**Settings:** restored from `data/ui_state.json` (your last session). "
        "Changes auto-save when you send a message or edit Advanced settings."
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

    try:
        async with LocalInferenceClient() as client:
            result = await client.chat(
                messages,
                temperature=temperature,
                max_tokens=int(max_tokens),
            )
            return result.content
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
                    "Chat history is saved automatically to `data/chat_history.json`."
                )
                chatbot = gr.Chatbot(height=420, label="Conversation", value=load_chat_history())
                with gr.Accordion("Advanced", open=True):
                    system_prompt_source = gr.Markdown(_settings_source_markdown())
                    with gr.Row():
                        load_prompt_btn = gr.Button(
                            "Import system prompt from file",
                            variant="secondary",
                        )
                        save_settings_btn = gr.Button(
                            "Save current settings as default",
                            variant="secondary",
                        )
                    system_prompt = gr.Textbox(
                        label="System prompt",
                        value=_SAVED["system_prompt"],
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
                            8192,
                            value=int(_SAVED["max_tokens"]),
                            step=128,
                            label="Max tokens",
                        )
                msg = gr.Textbox(
                    label="Your message",
                    placeholder="Explain sports arbitrage in simple terms…",
                    lines=2,
                )
                with gr.Row():
                    send = gr.Button("Send", variant="primary")
                    clear = gr.Button("Clear chat")

                def persist_settings_only(sys_p: str, temp: float, max_t: float) -> str:
                    save_ui_state(
                        system_prompt=sys_p,
                        temperature=temp,
                        max_tokens=int(max_t),
                    )
                    return _settings_source_markdown() + " _(saved just now)_"

                async def user_submit(
                    message: str,
                    history: list,
                    sys_p: str,
                    temp: float,
                    max_t: float,
                ) -> tuple[list, str, str]:
                    save_ui_state(
                        system_prompt=sys_p,
                        temperature=temp,
                        max_tokens=int(max_t),
                    )
                    reply = await chat_respond(message, history, sys_p, temp, max_t)
                    history = history or []
                    history.append([message, reply])
                    save_chat_history(history)
                    return history, "", _settings_source_markdown()

                def clear_chat() -> tuple[list, str, str]:
                    clear_chat_history()
                    return [], "", _settings_source_markdown()

                send.click(
                    user_submit,
                    inputs=[msg, chatbot, system_prompt, temperature, max_tokens],
                    outputs=[chatbot, msg, system_prompt_source],
                )
                msg.submit(
                    user_submit,
                    inputs=[msg, chatbot, system_prompt, temperature, max_tokens],
                    outputs=[chatbot, msg, system_prompt_source],
                )
                clear.click(
                    clear_chat,
                    outputs=[chatbot, msg, system_prompt_source],
                )
                save_settings_btn.click(
                    persist_settings_only,
                    inputs=[system_prompt, temperature, max_tokens],
                    outputs=[system_prompt_source],
                )
                for field in (system_prompt, temperature, max_tokens):
                    field.change(
                        persist_settings_only,
                        inputs=[system_prompt, temperature, max_tokens],
                        outputs=[system_prompt_source],
                    )

            with gr.Tab("🏗️ Architect (8B)"):
                gr.Markdown(
                    "Paste a **large** project prompt. The 8B model runs in **phases**: "
                    "JSON plan first, then one implementation chunk per phase. "
                    "Uses `prompts/system_8b_architect.txt` and saves your full prompt to "
                    "`data/last_mega_prompt.txt`."
                )
                mega_in = gr.Textbox(
                    label="Mega prompt",
                    lines=16,
                    placeholder="Paste your full architecture / scraping / arbitrage spec here…",
                )
                arch_phases = gr.Slider(
                    2,
                    8,
                    value=int(get_settings().architect_max_phases),
                    step=1,
                    label="Max implementation phases",
                )
                arch_run = gr.Button("Run phased architect", variant="primary")
                arch_status = gr.Markdown()
                arch_plan = gr.Code(label="Plan JSON", language="json")
                arch_output = gr.Textbox(
                    label="Generated output (all phases)",
                    lines=24,
                    max_lines=60,
                )

                async def run_architect_ui(mega: str, n_phases: float) -> tuple[str, str, str]:
                    if not (mega or "").strip():
                        return "⚠️ Paste a prompt first.", "{}", ""
                    await warmup_ollama()
                    try:
                        result = await run_architect(mega, max_phases=int(n_phases))
                    except Exception as exc:
                        return f"❌ {exc}", "{}", ""
                    plan_str = json.dumps(result.plan_json, indent=2)
                    chunks = [f"=== PLAN ===\n{plan_str}\n"]
                    for p in result.phases:
                        chunks.append(
                            f"\n\n=== PHASE {p.step}: {p.title} ({p.latency_ms:.0f} ms) ===\n{p.content}"
                        )
                    total_ms = sum(p.latency_ms for p in result.phases)
                    status = (
                        f"✅ Done — {len(result.phases)} phase(s), ~{total_ms/1000:.1f}s generation. "
                        "Copy code into `harvester/` under your repo."
                    )
                    return status, plan_str, "".join(chunks)

                arch_run.click(
                    run_architect_ui,
                    inputs=[mega_in, arch_phases],
                    outputs=[arch_status, arch_plan, arch_output],
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

        def import_system_prompt_from_file() -> tuple[str, str]:
            text, _ = get_system_prompt_info()
            save_ui_state(system_prompt=text)
            return text, _settings_source_markdown(from_file=True)

        async def reload_ollama_only() -> str:
            reload_settings()
            return await check_connection()

        async def wake_ollama() -> str:
            ok, msg = await warmup_ollama()
            return f"✅ {msg}" if ok else f"❌ {msg}"

        health_btn.click(check_connection, outputs=health_out)
        warmup_btn.click(wake_ollama, outputs=health_out)
        refresh_btn.click(reload_ollama_only, outputs=health_out)
        load_prompt_btn.click(
            import_system_prompt_from_file,
            outputs=[system_prompt, system_prompt_source],
        )

        async def on_page_load() -> tuple[str, list, str, float, float]:
            ok, warm_msg = await warmup_ollama()
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
                float(state["temperature"]),
                float(state["max_tokens"]),
            )

        demo.load(
            on_page_load,
            outputs=[health_out, chatbot, system_prompt_source, temperature, max_tokens],
        )

        gr.Markdown(
            "---\n"
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
