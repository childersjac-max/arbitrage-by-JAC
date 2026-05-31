#!/usr/bin/env python3
"""
Local web UI for your private LLM (Ollama).

Run:
  pip install -r requirements-app.txt
  python web_app.py

Then open http://127.0.0.1:7860 in your browser.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import webbrowser
from pathlib import Path

import gradio as gr

from config import get_settings, reload_settings
from paths import ENV_FILE, PACKAGE_DIR
from local_inference import LocalInferenceClient
from ollama_check import check_ollama_reachable, format_connection_help
from prompt_types import ChatMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Always run from local-llm/ so relative paths and .env stay consistent (Windows/Git Bash).
os.chdir(PACKAGE_DIR)
reload_settings()


def _status_markdown() -> str:
    cfg = get_settings()
    env_line = f"✅ `{ENV_FILE}`" if ENV_FILE.is_file() else f"⚠️ missing `{ENV_FILE}`"
    return (
        f"**Backend:** `{cfg.local_llm_backend.value}` · "
        f"**Model:** `{cfg.ollama_model}` · "
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

    cfg = get_settings()
    messages: list[ChatMessage] = []
    sys_text = (system_prompt or "").strip() or get_default_system_prompt()
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
            "Runs entirely on your machine via Ollama. Nothing is sent to cloud AI APIs."
        )
        status_md = gr.Markdown(_status_markdown())

        with gr.Row():
            health_btn = gr.Button("Check Ollama connection", variant="secondary")
            refresh_btn = gr.Button("Reload settings", variant="secondary")
        health_out = gr.Markdown(
            "Click **Check Ollama connection** before your first message."
        )

        with gr.Tabs():
            with gr.Tab("💬 Chat"):
                gr.Markdown(
                    "Ask anything—explanations, code, arbitrage ideas. "
                    "First message after startup may take 1–3 minutes."
                )
                chatbot = gr.Chatbot(height=420, label="Conversation")
                with gr.Accordion("Advanced", open=False):
                    system_prompt = gr.Textbox(
                        label="System prompt",
                        value=get_settings().local_llm_default_system,
                        lines=3,
                    )
                    with gr.Row():
                        temperature = gr.Slider(
                            0,
                            1.5,
                            value=get_settings().local_llm_prompt_temperature,
                            step=0.1,
                            label="Temperature",
                        )
                        max_tokens = gr.Slider(
                            128,
                            8192,
                            value=min(2048, get_settings().local_llm_prompt_max_tokens),
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

                async def user_submit(
                    message: str,
                    history: list,
                    sys_p: str,
                    temp: float,
                    max_t: int,
                ) -> tuple[list, str]:
                    reply = await chat_respond(message, history, sys_p, temp, max_t)
                    history = history or []
                    history.append([message, reply])
                    return history, ""

                send.click(
                    user_submit,
                    inputs=[msg, chatbot, system_prompt, temperature, max_tokens],
                    outputs=[chatbot, msg],
                )
                msg.submit(
                    user_submit,
                    inputs=[msg, chatbot, system_prompt, temperature, max_tokens],
                    outputs=[chatbot, msg],
                )
                clear.click(lambda: ([], ""), outputs=[chatbot, msg])

            with gr.Tab("🏷️ Normalize names"):
                gr.Markdown(
                    "Map messy sportsbook strings to official names (for your arb pipeline)."
                )
                with gr.Row():
                    with gr.Column():
                        fragments_text = gr.Textbox(
                            label="Raw names (one per line)",
                            lines=10,
                            placeholder="CHA Hornets\nCharlotte\nLakers -3.5",
                        )
                        reference_json = gr.Textbox(
                            label="Reference JSON (id → official name)",
                            lines=8,
                            value=json.dumps(
                                {
                                    "nba_cha": "Charlotte Hornets",
                                    "nba_lal": "Los Angeles Lakers",
                                    "nba_bos": "Boston Celtics",
                                },
                                indent=2,
                            ),
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

        async def reload_config() -> tuple[str, str]:
            reload_settings()
            ok, msg = await check_ollama_reachable()
            health = f"✅ {msg}\n\n{_status_markdown()}" if ok else f"❌ {msg}"
            return _status_markdown(), health

        health_btn.click(check_connection, outputs=health_out)
        refresh_btn.click(reload_config, outputs=[status_md, health_out])
        demo.load(check_connection, outputs=health_out)

        gr.Markdown(
            "---\n"
            "**Tips:** Keep Ollama running in the system tray. "
            f"CLI: `python prompt_cli.py --interactive` · Port: "
            f"`{get_settings().local_llm_ui_host}:{get_settings().local_llm_ui_port}`"
        )

    return demo


def _open_browser_when_ready(url: str, delay_sec: float = 2.0) -> None:
    """Open default browser (works when Gradio inbrowser=True fails on Windows/Git Bash)."""
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
    demo.launch(
        server_name=host,
        server_port=port,
        share=False,
        show_error=True,
        inbrowser=False,
    )


if __name__ == "__main__":
    main()
