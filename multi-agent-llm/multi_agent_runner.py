#!/usr/bin/env python3
"""
3-agent local LLM (standalone): Planner → Coder → Reviewer loop.

Standalone — only needs Ollama at http://127.0.0.1:11434
"""

from __future__ import annotations

import os
import sys

from pipeline_core import PipelineCallbacks, load_config, run_pipeline


def thought(msg: str) -> None:
    print(f"[THOUGHT] {msg}", flush=True)


def main() -> None:
    cfg = load_config()
    task = resolve_task()

    print(
        f"""
3-agent multi-agent runner (standalone)
  Ollama: {cfg.ollama_url}
  Planner:  {cfg.model_planner}
  Coder:    {cfg.model_coder}
  Reviewer: {cfg.model_reviewer}
  Max loops: {cfg.max_loops}  |  Delay: {cfg.delay_sec}s  |  Stream: {cfg.stream}
  Re-plan if score < {cfg.min_score_regenerate}
  Task: {task[:100]}{'...' if len(task) > 100 else ''}
""",
        flush=True,
    )

    def on_section(role: str, model: str) -> None:
        print(f"\n--- {role} ({model}) ---\n", flush=True)

    def on_token(token: str) -> None:
        print(token, end="", flush=True)

    callbacks = PipelineCallbacks(
        on_thought=thought,
        on_section=on_section,
        on_token=on_token,
    )
    result = run_pipeline(task, cfg, callbacks)
    print(f"\nFinal score: {result.best_score}/10\n", flush=True)


def resolve_task() -> str:
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-i", "--interactive"):
            return input("Enter task: ").strip()
        return " ".join(sys.argv[1:])
    if os.environ.get("MULTI_AGENT_TASK"):
        return os.environ["MULTI_AGENT_TASK"]
    if os.environ.get("PROMPT_INTERACTIVE", "").strip() in ("1", "true", "yes"):
        return input("Enter task: ").strip()
    return "Write a Python function to validate email addresses using only the standard library."


if __name__ == "__main__":
    main()
