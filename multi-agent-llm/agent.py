#!/usr/bin/env python3
"""
Drop-in replacement for ~/agent.py — uses your local Ollama (qwen2.5:3b by default).

  cd ~/Projects/multi-agent-llm
  pip install -r requirements-autogen.txt
  ollama pull qwen2.5:3b-instruct-q4_K_M
  python agent.py

Or copy to home:
  cp agent.py ~/agent.py
"""
from __future__ import annotations

import asyncio
import os
import sys

from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.ollama import OllamaChatCompletionClient

MODEL = os.environ.get("AUTOGEN_MODEL", "qwen2.5:3b-instruct-q4_K_M")
RUN_CODE = os.environ.get("AUTOGEN_RUN_CODE", "0").strip().lower() in ("1", "true", "yes")
TASK = " ".join(sys.argv[1:]) or "Write and run a Python script that sorts a list of numbers"


def model_client() -> OllamaChatCompletionClient:
    return OllamaChatCompletionClient(
        model=MODEL,
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": False,
            "family": "unknown",
            "structured_output": False,
        },
    )


async def main() -> None:
    client = model_client()
    termination = TextMentionTermination("TERMINATE")

    if RUN_CODE:
        executor = LocalCommandLineCodeExecutor(work_dir="workspace")
        assistant = AssistantAgent("assistant", model_client=client)
        code_executor = CodeExecutorAgent("code_executor", code_executor=executor)
        team = RoundRobinGroupChat([assistant, code_executor], termination_condition=termination)
    else:
        assistant = AssistantAgent(
            "assistant",
            model_client=client,
            system_message="You are a helpful assistant. End with TERMINATE when done.",
        )
        team = RoundRobinGroupChat([assistant], termination_condition=termination)

    print(f"Model: {MODEL} | code_exec={RUN_CODE}\nTask: {TASK}\n", flush=True)

    async for message in team.run_stream(task=TASK):
        print(f"\n--- {type(message).__name__} ---", flush=True)
        print(message, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
