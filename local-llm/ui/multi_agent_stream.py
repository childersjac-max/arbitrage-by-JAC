"""Stream 3-agent pipeline output into Gradio chat."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator

from multi_agent_bridge import get_pipeline_core, multi_agent_config_summary
from ollama_connect import check_ollama_reachable, format_connection_help
from ui.chat_history_fmt import append_turn, messages_to_tuples, set_last_assistant
from ui_state import save_chat_history
from workload_lock import WorkloadKind, ollama_workload


def thinking_status(elapsed: int, *, phase: str = "Multi-agent") -> str:
    dots = "." * ((elapsed // 2) % 3 + 1)
    return f"● {phase}{dots} ({elapsed}s)"


async def stream_multi_agent_turn(
    message: str,
    history: list[dict[str, str]],
) -> AsyncIterator[tuple[list[dict[str, str]], str, str]]:
    """
    Yields (messages, cleared_msg, status_md).

    Runs Planner → Coder → Reviewer in a worker thread; streams tokens into chat.
    """
    pc = get_pipeline_core()
    PipelineCallbacks = pc.PipelineCallbacks
    load_config = pc.load_config
    run_pipeline = pc.run_pipeline

    messages = list(history or [])
    status_md = multi_agent_config_summary()

    if not message or not message.strip():
        yield messages, "", status_md
        return

    ok, preflight = await check_ollama_reachable()
    if not ok:
        messages = append_turn(messages, message.strip(), f"❌ {preflight}")
        save_chat_history(messages_to_tuples(messages))
        yield messages, "", status_md
        return

    messages = append_turn(messages, message.strip(), "● Starting multi-agent pipeline…")
    yield messages, "", status_md

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()
    partial = ""
    started = time.monotonic()

    def enqueue(kind: str, payload: object = None) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, (kind, payload))

    def on_thought(msg: str) -> None:
        enqueue("thought", msg)

    def on_section(role: str, model: str) -> None:
        enqueue("section", f"\n\n--- **{role}** (`{model}`) ---\n\n")

    def on_token(token: str) -> None:
        enqueue("token", token)

    async def run_pipeline_task() -> None:
        try:
            async with ollama_workload(WorkloadKind.MULTI_AGENT):
                cfg = load_config()
                callbacks = PipelineCallbacks(
                    on_thought=on_thought,
                    on_section=on_section,
                    on_token=on_token,
                )
                await asyncio.to_thread(run_pipeline, message.strip(), cfg, callbacks)
            enqueue("done", None)
        except Exception as exc:
            enqueue("error", exc)

    task = asyncio.create_task(run_pipeline_task())

    try:
        while True:
            elapsed = int(time.monotonic() - started)
            try:
                kind, payload = await asyncio.wait_for(queue.get(), timeout=1.5)
            except asyncio.TimeoutError:
                if not partial:
                    messages = set_last_assistant(
                        messages,
                        thinking_status(elapsed, phase="Multi-agent running"),
                    )
                else:
                    messages = set_last_assistant(messages, partial + f"\n\n… ({elapsed}s)")
                yield messages, "", status_md
                continue

            if kind == "thought":
                line = f"\n\n> **[THOUGHT]** {payload}\n"
                partial += line
                messages = set_last_assistant(messages, partial)
                yield messages, "", status_md
                continue

            if kind == "section":
                partial += str(payload)
                messages = set_last_assistant(messages, partial)
                yield messages, "", status_md
                continue

            if kind == "token":
                partial += str(payload)
                messages = set_last_assistant(messages, partial)
                yield messages, "", status_md
                continue

            if kind == "error":
                exc = payload
                err = (
                    str(exc)
                    if isinstance(exc, ConnectionError)
                    else format_connection_help(exc if isinstance(exc, BaseException) else None)
                )
                messages = set_last_assistant(messages, partial + f"\n\n❌ {err}" if partial else f"❌ {err}")
                break

            if kind == "done":
                if not partial.strip():
                    messages = set_last_assistant(
                        messages,
                        "⚠️ Multi-agent finished with no output. Check Ollama models with `ollama list`.",
                    )
                else:
                    messages = set_last_assistant(messages, partial)
                break
    finally:
        if not task.done():
            task.cancel()

    save_chat_history(messages_to_tuples(messages))
    yield messages, "", status_md
