"""
Chat turn streaming — UI orchestration only; calls existing Ollama helpers unchanged.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator

from performance_profiles import (
    activate_performance_profile,
    chat_timeout_help,
    get_performance_profile,
)
from ollama_connect import (
    check_ollama_reachable,
    format_connection_help,
    get_effective_ollama_model,
    ollama_chat_completion,
    ollama_chat_stream,
    prefer_buffered_transport,
    warmup_ollama_model,
)
from ui.chat_history_fmt import (
    append_turn,
    is_placeholder_content,
    messages_to_tuples,
    set_last_assistant,
)
from ui_state import save_chat_history, save_ui_state

from ui.chat_helpers import (
    build_chat_api_messages,
    clamp_ui_max_tokens,
    reveal_text_chunks,
    settings_source_markdown,
)


def thinking_status(elapsed: int, *, phase: str = "Thinking") -> str:
    dots = "." * ((elapsed // 2) % 3 + 1)
    return f"● {phase}{dots} ({elapsed}s)"


async def stream_chat_turn(
    message: str,
    history: list[dict[str, str]],
    mode: str,
    temp: float,
    max_t: float,
) -> AsyncIterator[tuple[list[dict[str, str]], str, str, str, str]]:
    """
    Yields (messages, cleared_msg, settings_md, system_prompt_text, last_assistant_text).

    Inference path is identical to the previous web_app user_submit generator.
    """
    activate_performance_profile(mode)
    profile = get_performance_profile(mode)
    from performance_profiles import load_system_prompt_for_profile

    from project_context import prepend_project_context

    sys_from_file = prepend_project_context(load_system_prompt_for_profile(profile))
    meta = settings_source_markdown(mode)
    messages = list(history or [])

    if not message or not message.strip():
        yield messages, "", meta, sys_from_file, ""
        return

    max_t = clamp_ui_max_tokens(max_t, profile)
    temp = float(temp)
    save_ui_state(performance_profile=mode, temperature=temp, max_tokens=max_t)

    ok, preflight = await check_ollama_reachable()
    if not ok:
        messages = append_turn(messages, message.strip(), f"❌ {preflight}")
        save_chat_history(messages_to_tuples(messages))
        yield messages, "", meta, sys_from_file, ""
        return

    wait = (
        "● Loading model into memory…"
        if prefer_buffered_transport()
        else "● Connecting to Ollama…"
    )
    messages = append_turn(messages, message.strip(), wait)
    yield messages, "", meta, sys_from_file, ""

    pair_history = messages_to_tuples(messages[:-1] if messages else [])
    api_messages = build_chat_api_messages(
        message.strip(),
        pair_history,
        sys_from_file,
        max_history_turns=profile.max_history_turns,
    )
    timeout_sec = float(profile.timeout_sec)

    try:
        model = await get_effective_ollama_model(
            requested=profile.ollama_model,
            fast=profile.use_fast_model_picker,
        )
    except Exception as exc:
        messages = set_last_assistant(messages, format_connection_help(exc))
        save_chat_history(messages_to_tuples(messages))
        yield messages, "", meta, sys_from_file, ""
        return

    partial = ""
    started = time.monotonic()
    queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()
    use_buffered = prefer_buffered_transport()

    async def pump() -> None:
        try:
            if use_buffered and profile.warm_on_send:
                await warmup_ollama_model(model, num_ctx=profile.num_ctx)
            if use_buffered:
                text = await ollama_chat_completion(
                    api_messages,
                    model=model,
                    temperature=temp,
                    max_tokens=max_t,
                    num_ctx=profile.num_ctx,
                    workload_kind="chat",
                )
                if text:
                    await queue.put(("reveal", text))
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
                    text = await ollama_chat_completion(
                        api_messages,
                        model=model,
                        temperature=temp,
                        max_tokens=max_t,
                        num_ctx=profile.num_ctx,
                        workload_kind="chat",
                    )
                    if text:
                        await queue.put(("reveal", text))
                except Exception as exc2:
                    await queue.put(("e", exc2))
            else:
                await queue.put(("e", exc))
        await queue.put(("d", None))

    task = asyncio.create_task(pump())
    try:
        while True:
            elapsed = int(time.monotonic() - started)
            if elapsed > timeout_sec:
                task.cancel()
                suffix = chat_timeout_help(profile, elapsed_sec=elapsed)
                messages = set_last_assistant(messages, (partial or "●") + suffix)
                break

            try:
                kind, payload = await asyncio.wait_for(queue.get(), timeout=1.5)
            except asyncio.TimeoutError:
                if not partial:
                    phase = "Generating" if use_buffered else "Thinking"
                    messages = set_last_assistant(
                        messages, thinking_status(elapsed, phase=phase)
                    )
                else:
                    messages = set_last_assistant(
                        messages, partial + f" … ({elapsed}s)"
                    )
                yield messages, "", meta, sys_from_file, partial
                continue

            if kind == "reveal":
                async for chunk in reveal_text_chunks(str(payload)):
                    partial = chunk
                    messages = set_last_assistant(messages, chunk)
                    yield messages, "", meta, sys_from_file, partial
                continue
            if kind == "d":
                if not partial.strip():
                    messages = set_last_assistant(
                        messages,
                        "⚠️ Empty reply. Try **Fast** profile or a shorter prompt.",
                    )
                else:
                    messages = set_last_assistant(messages, partial)
                break
            if kind == "e":
                exc = payload
                err = (
                    str(exc)
                    if isinstance(exc, ConnectionError)
                    else format_connection_help(
                        exc if isinstance(exc, BaseException) else None
                    )
                )
                messages = set_last_assistant(messages, err)
                break
            partial += str(payload)
            messages = set_last_assistant(messages, partial)
            yield messages, "", meta, sys_from_file, partial
    finally:
        if not task.done():
            task.cancel()

    save_chat_history(messages_to_tuples(messages))
    final = partial if not is_placeholder_content(partial) else ""
    yield messages, "", meta, sys_from_file, final
