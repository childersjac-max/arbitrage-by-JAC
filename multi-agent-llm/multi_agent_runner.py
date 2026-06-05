#!/usr/bin/env python3
"""
3-agent local LLM (standalone): Planner → Coder → Reviewer loop.

Standalone — only needs Ollama at http://127.0.0.1:11434

Novice overview:
  - Planner breaks your task into steps (fast 3B model).
  - Coder writes the implementation (7B coder model).
  - Reviewer scores and suggests fixes (fast 3B model).
  - [THOUGHT] lines explain each step; text streams as it is generated.
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

# Loaded fully in load_config()
CFG: dict = {}


def load_dotenv() -> None:
    if not ENV_FILE.is_file():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def load_config() -> None:
    load_dotenv()
    planner = os.environ.get(
        "MODEL_PLANNER",
        os.environ.get("MULTI_AGENT_MODEL_PLANNER", "qwen2.5:3b-instruct-q4_K_M"),
    )
    coder = os.environ.get(
        "MODEL_CODER",
        os.environ.get("MULTI_AGENT_MODEL_A", "qwen2.5-coder:7b-instruct-q4_K_M"),
    )
    reviewer = os.environ.get(
        "MODEL_REVIEWER",
        os.environ.get("MULTI_AGENT_MODEL_B", "qwen2.5:3b-instruct-q4_K_M"),
    )
    CFG.update(
        {
            "ollama_url": os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/generate"),
            "model_planner": planner,
            "model_coder": coder,
            "model_reviewer": reviewer,
            "max_loops": int(os.environ.get("MAX_LOOPS", os.environ.get("MULTI_AGENT_MAX_LOOPS", "3"))),
            "delay_sec": float(os.environ.get("DELAY_BETWEEN_CALLS", "2")),
            "min_score_regenerate": int(os.environ.get("MIN_SCORE_REGENERATE", "6")),
            "stream": os.environ.get("STREAM_OUTPUT", "1").strip() not in ("0", "false", "False"),
            "timeout_planner": int(os.environ.get("TIMEOUT_PLANNER_SEC", "120")),
            "timeout_coder": int(os.environ.get("TIMEOUT_CODER_SEC", "600")),
            "timeout_reviewer": int(os.environ.get("TIMEOUT_REVIEWER_SEC", "180")),
            "default_task": os.environ.get(
                "MULTI_AGENT_TASK",
                "Write a Python function to validate email addresses using only the standard library.",
            ),
            "system_planner": os.environ.get(
                "SYSTEM_PLANNER",
                """You are a planning assistant.

Break the task into clear steps:
- Inputs
- Logic
- Edge cases

Output concise structured steps only. No code yet.""",
            ),
            "system_coder": os.environ.get(
                "SYSTEM_CODER",
                """You are a coding assistant.
Write a clean working implementation.
Follow the plan exactly.
Return code with brief comments only where helpful.""",
            ),
            "system_reviewer": os.environ.get(
                "SYSTEM_REVIEWER",
                """You are a strict code reviewer.

Return exactly:

Bugs:
- ...

Improvements:
- ...

Revised Code:
<full improved code>

Score: X/10
Confidence: High/Medium/Low""",
            ),
        }
    )


def thought(msg: str) -> None:
    print(f"[THOUGHT] {msg}", flush=True)


def cpu_pause() -> None:
    """Novice note: short pause so CPU/RAM can settle between heavy model calls."""
    delay = CFG["delay_sec"]
    if delay > 0:
        thought(f"CPU pause {delay}s (keeps 16GB RAM stable)...")
        time.sleep(delay)


def ask(
    model: str,
    prompt: str,
    *,
    system: str | None = None,
    role_description: str = "",
    timeout_sec: int = 600,
) -> str:
    """
    Send one request to Ollama /api/generate.
    Novice note: messenger between you and the local AI; streams tokens when enabled.
    """
    thought(f"Contacting {model} — {role_description or 'working'}...")
    stream = CFG["stream"]
    payload: dict = {"model": model, "prompt": prompt, "stream": stream}
    if system:
        payload["system"] = system

    try:
        resp = requests.post(
            CFG["ollama_url"],
            json=payload,
            stream=stream,
            timeout=timeout_sec,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        thought(f"Connection failed: {exc}")
        thought("Start Ollama from the Start menu, then: ollama list")
        raise SystemExit(1) from exc

    if not stream:
        text = str(resp.json().get("response", ""))
        thought(f"{model} finished.")
        return text

    parts: list[str] = []
    print(f"\n--- {role_description} ({model}) ---\n", flush=True)
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
    for line in feedback.splitlines():
        if "Score:" in line:
            try:
                return int(line.split(":", 1)[1].strip().split("/")[0].strip())
            except ValueError:
                pass
    m = re.search(r"Score:\s*(\d+)\s*/\s*10", feedback, re.I)
    return int(m.group(1)) if m else 0


def parse_confidence(feedback: str) -> str:
    m = re.search(r"Confidence:\s*(High|Medium|Low)", feedback, re.I)
    return m.group(1).capitalize() if m else "Unknown"


def extract_revised_code(feedback: str) -> str | None:
    marker = "Revised Code:"
    if marker not in feedback:
        return None
    block = feedback.split(marker, 1)[1]
    if "Score:" in block:
        block = block.split("Score:", 1)[0]
    if "Confidence:" in block:
        block = block.split("Confidence:", 1)[0]
    block = block.strip()
    if block.startswith("```"):
        block = re.sub(r"^```\w*\n?", "", block)
        block = re.sub(r"\n?```\s*$", "", block)
    return block.strip() or None


def no_bugs_reported(feedback: str) -> bool:
    return bool(
        re.search(r"Bugs:\s*\n\s*-\s*None\b", feedback, re.I)
        or "Bugs:\n- None" in feedback
        or "Bugs:\nNone" in feedback
    )


def build_plan(task: str, *, replan: bool = False) -> str:
    label = "Re-planning" if replan else "Planning"
    thought(f"{label}: breaking the task into steps (Planner / 3B)...")
    prompt = task
    if replan:
        prompt = (
            "Previous attempt scored too low. Create a NEW plan from scratch.\n\n"
            f"TASK:\n{task}"
        )
    plan = ask(
        CFG["model_planner"],
        prompt,
        system=CFG["system_planner"],
        role_description="Planner — task decomposition",
        timeout_sec=CFG["timeout_planner"],
    )
    print("\n=== PLAN ===\n", flush=True)
    print(plan, flush=True)
    print("\n", flush=True)
    return plan


def run_pipeline(task: str) -> None:
    original_task = task
    plan = build_plan(task)
    cpu_pause()

    best_score = -1
    best_output = ""
    current_task = task

    for i in range(CFG["max_loops"]):
        print(f"\n{'=' * 60}\n=== Iteration {i + 1} / {CFG['max_loops']} ===\n{'=' * 60}", flush=True)

        thought("Coder implements the plan (7B — slowest step on CPU).")
        code_prompt = f"""Use this plan:

{plan}

Original task:
{original_task}

Current focus:
{current_task}
"""
        solution = ask(
            CFG["model_coder"],
            code_prompt,
            system=CFG["system_coder"],
            role_description="Coder — implementation",
            timeout_sec=CFG["timeout_coder"],
        )
        cpu_pause()

        thought("Reviewer checks bugs, improvements, and score (3B).")
        review_prompt = f"Review and improve this code:\n\n{solution}"
        feedback = ask(
            CFG["model_reviewer"],
            review_prompt,
            system=CFG["system_reviewer"],
            role_description="Reviewer — critique + score",
            timeout_sec=CFG["timeout_reviewer"],
        )
        cpu_pause()

        score = parse_score(feedback)
        confidence = parse_confidence(feedback)
        print(f"\nScore: {score}/10  |  Confidence: {confidence}\n", flush=True)

        if score > best_score:
            best_score = score
            best_output = extract_revised_code(feedback) or feedback

        if no_bugs_reported(feedback) or score >= 9:
            thought("High quality — stopping early.")
            break

        if score < CFG["min_score_regenerate"]:
            thought(
                f"Score below {CFG['min_score_regenerate']} — re-planning from scratch next round."
            )
            plan = build_plan(original_task, replan=True)
            cpu_pause()
            current_task = original_task
        else:
            thought("Feeding reviewer feedback into the next coder round.")
            current_task = f"Improve using this feedback:\n\n{feedback}"

    print("\n" + "=" * 60)
    print("BEST SOLUTION")
    print("=" * 60 + "\n")
    print(best_output or "(none)")
    print(f"\nFinal score: {best_score}/10\n")


def resolve_task() -> str:
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-i", "--interactive"):
            return input("Enter task: ").strip()
        return " ".join(sys.argv[1:])
    if sys.environ.get("MULTI_AGENT_TASK"):
        return os.environ["MULTI_AGENT_TASK"]
    if sys.environ.get("PROMPT_INTERACTIVE", "").strip() in ("1", "true", "yes"):
        return input("Enter task: ").strip()
    return CFG["default_task"]


def main() -> None:
    load_config()
    task = resolve_task()

    print(
        f"""
3-agent multi-agent runner (standalone)
  Ollama: {CFG['ollama_url']}
  Planner:  {CFG['model_planner']}
  Coder:    {CFG['model_coder']}
  Reviewer: {CFG['model_reviewer']}
  Max loops: {CFG['max_loops']}  |  Delay: {CFG['delay_sec']}s  |  Stream: {CFG['stream']}
  Re-plan if score < {CFG['min_score_regenerate']}
  Task: {task[:100]}{'...' if len(task) > 100 else ''}
""",
        flush=True,
    )

    run_pipeline(task)


if __name__ == "__main__":
    main()
