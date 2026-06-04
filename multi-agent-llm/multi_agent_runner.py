#!/usr/bin/env python3
"""
Multi-agent local LLM: coder generates, reviewer critiques.
Standalone — only needs Ollama at http://127.0.0.1:11434

Novice overview:
  - Model A writes code for your task.
  - Model B reviews it and scores it.
  - The loop repeats until the score is good or max rounds hit.
  - [THOUGHT] lines show what is happening live.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
DEFAULT_MODEL_A = "qwen2.5-coder:7b-instruct-q4_K_M"
DEFAULT_MODEL_B = "qwen2.5:3b-instruct-q4_K_M"


def load_dotenv() -> None:
    if not ENV_FILE.is_file():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def thought(msg: str) -> None:
    print(f"[THOUGHT] {msg}", flush=True)


def ask(
    model: str,
    prompt: str,
    *,
    system: str | None = None,
    role_description: str = "",
    stream_thoughts: bool = True,
    timeout_sec: int = 600,
) -> str:
    """
    Send one request to Ollama /api/generate.

    Novice note: This is the messenger — it sends your prompt to the AI
    and collects the full reply (streaming tokens to the screen as they arrive).
    """
    thought(f"Contacting {model} — {role_description or 'working'}...")
    payload: dict = {
        "model": model,
        "prompt": prompt,
        "stream": stream_thoughts,
    }
    if system:
        payload["system"] = system

    try:
        resp = requests.post(OLLAMA_URL, json=payload, stream=stream_thoughts, timeout=timeout_sec)
        resp.raise_for_status()
    except requests.RequestException as exc:
        thought(f"Connection failed: {exc}")
        thought("Is Ollama running? Start it from the Start menu, then: ollama list")
        raise SystemExit(1) from exc

    if not stream_thoughts:
        data = resp.json()
        thought(f"{model} finished.")
        return str(data.get("response", ""))

    parts: list[str] = []
    print(f"\n--- {model} ({role_description}) ---\n", flush=True)
    for raw in resp.iter_lines():
        if not raw:
            continue
        try:
            chunk = json.loads(raw)
        except json.JSONDecodeError:
            continue
        token = chunk.get("response") or ""
        if token:
            print(token, end="", flush=True)
            parts.append(token)
        if chunk.get("done"):
            break
    print("\n", flush=True)
    thought(f"{model} finished.")
    return "".join(parts)


def parse_score(feedback: str) -> int:
    """Novice note: looks for a line like 'Score: 8/10' and reads the number."""
    for line in feedback.splitlines():
        if "Score:" in line:
            try:
                tail = line.split(":", 1)[1].strip()
                return int(tail.split("/")[0].strip())
            except ValueError:
                return 0
    m = re.search(r"Score:\s*(\d+)\s*/\s*10", feedback, re.I)
    return int(m.group(1)) if m else 0


def extract_revised_code(feedback: str) -> str | None:
    """Pull text under 'Revised Code:' if the reviewer formatted correctly."""
    marker = "Revised Code:"
    if marker not in feedback:
        return None
    block = feedback.split(marker, 1)[1]
    if "Score:" in block:
        block = block.split("Score:", 1)[0]
    block = block.strip()
    if block.startswith("```"):
        block = re.sub(r"^```\w*\n?", "", block)
        block = re.sub(r"\n?```\s*$", "", block)
    return block.strip() or None


def run_loop(
    task: str,
    *,
    model_a: str,
    model_b: str,
    system_a: str,
    system_b: str,
    max_loops: int,
) -> None:
    best_solution: str | None = None
    best_score = -1
    current_task = task

    for i in range(max_loops):
        print(f"\n{'=' * 60}\n=== Iteration {i + 1} / {max_loops} ===\n{'=' * 60}", flush=True)

        thought("Model A will draft code for the current task.")
        solution = ask(
            model_a,
            current_task,
            system=system_a,
            role_description="Code generation (Model A)",
        )
        print("\nModel A output saved for review.\n", flush=True)

        thought("Model B will review security, logic, and style.")
        review_prompt = f"Review the following code and improve it.\n\nCODE:\n{solution}"
        feedback = ask(
            model_b,
            review_prompt,
            system=system_b,
            role_description="Code review (Model B)",
        )

        score = parse_score(feedback)
        print(f"\nScore this round: {score}/10\n", flush=True)

        if score > best_score:
            best_score = score
            revised = extract_revised_code(feedback) or feedback
            best_solution = revised

        if "Bugs:\n- None" in feedback or "Bugs:\nNone" in feedback or re.search(
            r"Bugs:\s*\n\s*-\s*None", feedback, re.I
        ):
            thought("Reviewer reported no bugs — stopping early.")
            break

        if score >= 9:
            thought("High score — stopping early.")
            break

        thought("Preparing the next round using reviewer feedback.")
        current_task = f"Improve the solution using this review:\n\n{feedback}"

    print("\n" + "=" * 60)
    print("BEST SOLUTION FOUND")
    print("=" * 60 + "\n")
    print(best_solution or "(none)")
    print(f"\nFinal score: {best_score}/10\n")


def main() -> None:
    load_dotenv()
    model_a = os.environ.get("MULTI_AGENT_MODEL_A", DEFAULT_MODEL_A)
    model_b = os.environ.get("MULTI_AGENT_MODEL_B", DEFAULT_MODEL_B)
    max_loops = int(os.environ.get("MULTI_AGENT_MAX_LOOPS", "3"))
    task = os.environ.get(
        "MULTI_AGENT_TASK",
        "Write a Python function to validate email addresses using only the standard library.",
    )
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])

    system_a = os.environ.get(
        "MULTI_AGENT_SYSTEM_A",
        "You are a coding assistant. Produce correct, clean, working Python. Be concise.",
    )
    system_b = os.environ.get(
        "MULTI_AGENT_SYSTEM_B",
        """You are a strict code reviewer. Always respond in this exact format:
Bugs:
- ...
Improvements:
- ...
Revised Code:
<full improved code>
Score: X/10""",
    )

    print(
        f"""
Multi-agent runner (standalone)
  Ollama: {OLLAMA_URL}
  Model A (coder): {model_a}
  Model B (reviewer): {model_b}
  Max loops: {max_loops}
  Task: {task[:120]}{'...' if len(task) > 120 else ''}
""",
        flush=True,
    )

    run_loop(
        task,
        model_a=model_a,
        model_b=model_b,
        system_a=system_a,
        system_b=system_b,
        max_loops=max_loops,
    )


if __name__ == "__main__":
    main()
