"""Copilot-style chat tab for Gradio (inference via ui.chat_engine)."""

from __future__ import annotations

from dataclasses import dataclass

import gradio as gr

from performance_profiles import (
    PerformanceProfile,
    PerformanceProfileName,
    activate_performance_profile,
    get_performance_profile,
    load_system_prompt_for_profile,
)
from multi_agent_bridge import multi_agent_config_summary
from ui.chat_engine import stream_chat_turn
from ui.multi_agent_stream import stream_multi_agent_turn
from ui.chat_helpers import settings_source_markdown
from ui.chat_history_fmt import (
    last_user_message,
    strip_trailing_assistant,
    tuples_to_messages,
)
from ui.copilot_styles import SUGGESTED_PROMPTS, render_header_html
from ui_state import clear_chat_history, load_chat_history, save_ui_state


def load_messages_from_disk() -> list[dict[str, str]]:
    return tuples_to_messages(load_chat_history())


@dataclass
class ChatTabRefs:
    chat_workflow: gr.Radio
    perf_profile: gr.Radio
    header_html: gr.HTML
    status_bar: gr.Markdown
    chatbot: gr.Chatbot
    msg: gr.Textbox
    last_reply: gr.State
    system_prompt: gr.Textbox
    system_prompt_source: gr.Markdown
    temperature: gr.Slider
    max_tokens: gr.Slider
    send: gr.Button


def mount_copilot_chat_tab(
    saved_state: dict,
    initial_profile: PerformanceProfile,
) -> ChatTabRefs:
    """Build Copilot-like chat UI inside the current gr.Blocks context."""
    initial_messages = load_messages_from_disk()
    prof_name = initial_profile.name.value
    initial_workflow = str(saved_state.get("chat_workflow", "single"))
    if initial_workflow not in ("single", "multi_agent"):
        initial_workflow = "single"

    with gr.Column(elem_classes=["copilot-app", "copilot-chat-tab"]):
        header_html = gr.HTML(render_header_html(initial_profile))
        status_bar = gr.Markdown(
            value=f"**Profile:** {initial_profile.label} · **Model:** `{initial_profile.ollama_model}` · Ready",
            elem_classes=["copilot-status-bar"],
        )

        with gr.Row(elem_classes=["copilot-profile"]):
            chat_workflow = gr.Radio(
                choices=[
                    ("💬 Single chat", "single"),
                    ("🤖 Multi-agent (Planner → Coder → Reviewer)", "multi_agent"),
                ],
                value=initial_workflow,
                label="Chat mode",
                scale=4,
            )

        with gr.Row(elem_classes=["copilot-profile"]):
            perf_profile = gr.Radio(
                choices=[
                    ("⚡ Fast", PerformanceProfileName.FAST.value),
                    ("⚖️ Balanced", PerformanceProfileName.BALANCED.value),
                    ("🎯 Quality (7B, slow)", PerformanceProfileName.QUALITY.value),
                ],
                value=prof_name,
                label="Performance",
                scale=3,
            )

        chatbot = gr.Chatbot(
            value=initial_messages,
            type="messages",
            height=520,
            show_label=False,
            elem_id="copilot-chat",
            show_copy_button=True,
        )

        gr.Markdown("**Suggested**", elem_classes=["copilot-suggestions-label"])
        with gr.Row(elem_classes=["copilot-suggestions"]):
            suggest_btns = []
            for prompt in SUGGESTED_PROMPTS:
                suggest_btns.append(
                    gr.Button(prompt[:42] + ("…" if len(prompt) > 42 else ""), size="sm")
                )

        with gr.Column(elem_classes=["copilot-composer-wrap"]):
            with gr.Group(elem_classes=["copilot-composer"]):
                msg = gr.Textbox(
                    show_label=False,
                    placeholder="Message Local Copilot… (Enter to send, Shift+Enter for new line)",
                    lines=3,
                    max_lines=8,
                    elem_id="copilot-input",
                )
                with gr.Row():
                    send = gr.Button("Send ↑", variant="primary", elem_classes=["copilot-send-btn"])
                    regenerate_btn = gr.Button("↻ Regenerate", size="sm")
                    edit_last_btn = gr.Button("✎ Edit last", size="sm")
                    clear_btn = gr.Button("New chat", size="sm")

        last_reply = gr.State("")

        with gr.Accordion("Settings & system prompt", open=False):
            system_prompt_source = gr.Markdown(settings_source_markdown(prof_name))
            with gr.Row():
                load_prompt_btn = gr.Button("Reload system prompt", size="sm")
                save_settings_btn = gr.Button("Save settings", size="sm")
            system_prompt = gr.Textbox(
                label="System prompt",
                value=load_system_prompt_for_profile(initial_profile),
                lines=10,
            )
            with gr.Row():
                temperature = gr.Slider(
                    0,
                    1.5,
                    value=float(saved_state["temperature"]),
                    step=0.1,
                    label="Temperature",
                )
                max_tokens = gr.Slider(
                    128,
                    initial_profile.max_tokens_cap,
                    value=int(saved_state["max_tokens"]),
                    step=64,
                    label=f"Max tokens (cap {initial_profile.max_tokens_cap})",
                )

        refs = ChatTabRefs(
            chat_workflow=chat_workflow,
            perf_profile=perf_profile,
            header_html=header_html,
            status_bar=status_bar,
            chatbot=chatbot,
            msg=msg,
            last_reply=last_reply,
            system_prompt=system_prompt,
            system_prompt_source=system_prompt_source,
            temperature=temperature,
            max_tokens=max_tokens,
            send=send,
        )

        def _profile_status(mode: str) -> str:
            p = get_performance_profile(mode)
            return f"**Profile:** {p.label} · **Model:** `{p.ollama_model}`"

        def apply_performance_profile_ui(mode: str) -> tuple[float, dict, str, str, str, str]:
            activate_performance_profile(mode)
            profile = get_performance_profile(mode)
            save_ui_state(
                performance_profile=mode,
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
                    label=f"Max tokens (cap {profile.max_tokens_cap})",
                ),
                load_system_prompt_for_profile(profile),
                settings_source_markdown(mode),
                _profile_status(mode),
                render_header_html(profile),
            )

        def _status_for_workflow(workflow: str, mode: str) -> str:
            if workflow == "multi_agent":
                try:
                    return multi_agent_config_summary()
                except FileNotFoundError as exc:
                    return f"⚠️ {exc}"
            return _profile_status(mode)

        async def run_turn(
            message: str,
            history: list,
            workflow: str,
            mode: str,
            _sys_p: str,
            temp: float,
            max_t: float,
        ):
            save_ui_state(chat_workflow=workflow)
            if workflow == "multi_agent":
                async for hist, cleared, status in stream_multi_agent_turn(message, history or []):
                    yield (
                        hist,
                        cleared,
                        status,
                        _sys_p,
                        "",
                        status,
                        render_header_html(get_performance_profile(mode)),
                    )
                return

            async for hist, cleared, meta, sys_p, last in stream_chat_turn(
                message, history or [], mode, temp, max_t
            ):
                yield (
                    hist,
                    cleared,
                    meta,
                    sys_p,
                    last,
                    _profile_status(mode),
                    render_header_html(get_performance_profile(mode)),
                )

        inputs = [msg, chatbot, chat_workflow, perf_profile, system_prompt, temperature, max_tokens]
        outputs = [
            chatbot,
            msg,
            system_prompt_source,
            system_prompt,
            last_reply,
            status_bar,
            header_html,
        ]

        send.click(
            run_turn,
            inputs=inputs,
            outputs=outputs,
            show_progress="minimal",
        )
        msg.submit(
            run_turn,
            inputs=inputs,
            outputs=outputs,
            show_progress="minimal",
        )

        async def regenerate(history, workflow, mode, _sys_p, temp, max_t):
            hist = strip_trailing_assistant(list(history or []))
            user = last_user_message(hist)
            if not user:
                yield (
                    history,
                    "",
                    settings_source_markdown(mode),
                    _sys_p,
                    "",
                    _status_for_workflow(workflow, mode),
                    render_header_html(get_performance_profile(mode)),
                )
                return
            async for out in run_turn(user, hist, workflow, mode, _sys_p, temp, max_t):
                yield out

        regenerate_btn.click(
            regenerate,
            inputs=[chatbot, chat_workflow, perf_profile, system_prompt, temperature, max_tokens],
            outputs=outputs,
            show_progress="minimal",
        )

        def on_workflow_change(workflow: str, mode: str) -> str:
            save_ui_state(chat_workflow=workflow)
            return _status_for_workflow(workflow, mode)

        chat_workflow.change(
            on_workflow_change,
            inputs=[chat_workflow, perf_profile],
            outputs=[status_bar],
        )

        def prepare_edit(history):
            user = last_user_message(list(history or []))
            return user or ""

        edit_last_btn.click(prepare_edit, inputs=[chatbot], outputs=[msg])

        def clear_all():
            clear_chat_history()
            p = get_performance_profile()
            return [], "", settings_source_markdown(p.name.value), _profile_status(p.name.value), render_header_html(p)

        clear_btn.click(
            clear_all,
            outputs=[chatbot, msg, system_prompt_source, status_bar, header_html],
        )

        def persist_settings_only(mode: str, temp: float, max_t: float) -> str:
            save_ui_state(
                performance_profile=mode,
                temperature=temp,
                max_tokens=int(max_t),
            )
            return settings_source_markdown(mode) + " _(saved)_"

        save_settings_btn.click(
            persist_settings_only,
            inputs=[perf_profile, temperature, max_tokens],
            outputs=[system_prompt_source],
        )
        for field in (temperature, max_tokens):
            field.change(
                persist_settings_only,
                inputs=[perf_profile, temperature, max_tokens],
                outputs=[system_prompt_source],
            )

        perf_profile.change(
            apply_performance_profile_ui,
            inputs=[perf_profile],
            outputs=[
                temperature,
                max_tokens,
                system_prompt,
                system_prompt_source,
                status_bar,
                header_html,
            ],
        )

        def reload_system_prompt(mode: str) -> tuple[str, str]:
            profile = get_performance_profile(mode)
            text = load_system_prompt_for_profile(profile)
            return text, settings_source_markdown(mode, reloaded=True)

        load_prompt_btn.click(
            reload_system_prompt,
            inputs=[perf_profile],
            outputs=[system_prompt, system_prompt_source],
        )

        for btn, full_prompt in zip(suggest_btns, SUGGESTED_PROMPTS):
            btn.click(lambda p=full_prompt: p, outputs=[msg])

    return refs
