#!/usr/bin/env python3
"""
AutoGen + Ollama (standalone) — assistant + optional code executor.

Uses the SAME models as multi_agent_runner.py (.env MODEL_PLANNER / MODEL_CODER).

Novice note:
  - Ollama must be running (Start menu).
  - model= must match `ollama list` exactly.
  - Start with AUTOGEN_RUN_CODE=0 (chat only), then enable code execution.

Run:
  python autogen_agent.py "Your task here"
  python autogen_agent.py --interactive
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
WORK_DIR = ROOT / "autogen_workspace"


def load_dotenv() -> None:
    if not ENV_FILE.is_file():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


def model_name() -> str:
    return os.environ.get(
        "AUTOGEN_MODEL",
        os.environ.get("MODEL_PLANNER", "qwen2.5:3b-instruct-q4_K_M"),
    )


def qwen_model_info() -> dict:
    """Required for full Ollama tags like qwen2.5:3b-instruct-q4_K_M."""
    return {
        "vision": False,
        "function_calling": True,
        "json_output": False,
        "family": "qwen2.5",
        "structured_output": False,
    }


def resolve_task() -> str:
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-i", "--interactive"):
            return input("Enter task: ").strip()
        return " ".join(sys.argv[1:])
    return os.environ.get(
        "AUTOGEN_TASK",
        "Write and run a Python script that sorts a list of numbers.",
    )


async def main() -> None:
    load_dotenv()
    task = resolve_task()
    model = model_name()
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    run_code = os.environ.get("AUTOGEN_RUN_CODE", "0").strip() in ("1", "true", "yes")
    num_predict = int(os.environ.get("AUTOGEN_NUM_PREDICT", "512"))

    print(
        f"""
AutoGen + Ollama (standalone)
  Host:   {host}
  Model:  {model}
  Code execution: {run_code}
  Task:   {task[:80]}{'...' if len(task) > 80 else ''}
""",
        flush=True,
    )

    try:
        from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
        from autogen_agentchat.conditions import TextMentionTermination
        from autogen_agentchat.teams import RoundRobinGroupChat
        from autogen_ext.models.ollama import OllamaChatCompletionClient
    except ImportError as exc:
        print(
            "Missing AutoGen. Install in this folder's venv:\n"
            '  pip install -r requirements-autogen.txt\n',
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    model_client = OllamaChatCompletionClient(
        model=model,
        host=host,
        model_info=qwen_model_info(),
        num_predict=num_predict,
        num_ctx=int(os.environ.get("AUTOGEN_NUM_CTX", "2048")),
    )

    assistant = AssistantAgent("assistant", model_client=model_client)

    if run_code:
        from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor

        WORK_DIR.mkdir(parents=True, exist_ok=True)
        executor = LocalCommandLineCodeExecutor(work_dir=str(WORK_DIR))
        code_executor = CodeExecutorAgent("code_executor", code_executor=executor)
        agents = [assistant, code_executor]
        print("WARNING: Code will run on your PC. Review autogen_workspace/ output.\n", flush=True)
    else:
        agents = [assistant]
        print("Chat-only mode (no code execution). Set AUTOGEN_RUN_CODE=1 to enable.\n", flush=True)

    termination = TextMentionTermination("TERMINATE")
    team = RoundRobinGroupChat(agents, termination_condition=termination)

    print("Streaming messages (Ctrl+C to stop)...\n", flush=True)
    try:
        async for message in team.run_stream(task=task):
            print(f"\n--- {type(message).__name__} ---", flush=True)
            print(message, flush=True)
    finally:
        await model_client.close()

    print("\nDone. Say TERMINATE in the task or wait for the agent to finish.\n", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
