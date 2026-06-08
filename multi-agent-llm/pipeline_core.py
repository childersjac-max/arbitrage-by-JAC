"""Shared 3-agent pipeline (Planner → Coder → Reviewer) for CLI and Gradio UI."""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
PROMPTS_DIR = ROOT / "prompts"

from project_context import with_project_context  # noqa: E402


def _read_prompt_file(name: str, fallback: str) -> str:
    """Load prompt text from prompts/*.txt — safe to edit without breaking Python syntax."""
    path = PROMPTS_DIR / name
    if path.is_file():
        text = path.read_text(encoding="utf-8").strip()
        if text:
            return text
    return fallback


def _default_planner_prompt() -> str:
    return _read_prompt_file("system_planner.txt", "You are a planning assistant. Output steps only, no code.")


def _default_coder_prompt() -> str:
    return _read_prompt_file(
        "system_coder.txt",
        "You are a coding assistant. Write clean working code following the plan.",
    )


def _default_reviewer_prompt() -> str:
    return _read_prompt_file(
        "system_reviewer.txt",
        "You are a strict code reviewer. Return Bugs, Improvements, Revised Code, Score X/10, Confidence.",
    )


@dataclass
class MultiAgentConfig:
    ollama_url: str = "http://127.0.0.1:11434/api/generate"
    model_planner: str = "qwen2.5:3b-instruct-q4_K_M"
    model_coder: str = "qwen2.5-coder:7b-instruct-q4_K_M"
    model_reviewer: str = "qwen2.5:3b-instruct-q4_K_M"
    max_loops: int = 3
    delay_sec: float = 2.0
    min_score_regenerate: int = 6
    stream: bool = True
    timeout_planner: int = 120
    timeout_coder: int = 600
    timeout_reviewer: int = 180
    system_planner: str = ""
    system_coder: str = ""
    system_reviewer: str = ""

    def __post_init__(self) -> None:
        if not self.system_planner:
            self.system_planner = with_project_context(_default_planner_prompt())
        else:
            self.system_planner = with_project_context(self.system_planner)
        if not self.system_coder:
            self.system_coder = with_project_context(_default_coder_prompt())
        else:
            self.system_coder = with_project_context(self.system_coder)
        if not self.system_reviewer:
            self.system_reviewer = with_project_context(_default_reviewer_prompt())
        else:
            self.system_reviewer = with_project_context(self.system_reviewer)


@dataclass
class PipelineResult:
    best_output: str
    best_score: int
    plan: str
    iterations: int


@dataclass
class PipelineCallbacks:
    on_thought: Callable[[str], None] | None = None
    on_section: Callable[[str, str], None] | None = None
    on_token: Callable[[str], None] | None = None
    on_pause: Callable[[float], None] | None = None


def load_dotenv() -> None:
    if not ENV_FILE.is_file():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def load_config() -> MultiAgentConfig:
    load_dotenv()
    return MultiAgentConfig(
        ollama_url=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/generate"),
        model_planner=os.environ.get(
            "MODEL_PLANNER",
            os.environ.get("MULTI_AGENT_MODEL_PLANNER", "qwen2.5:3b-instruct-q4_K_M"),
        ),
        model_coder=os.environ.get(
            "MODEL_CODER",
            os.environ.get("MULTI_AGENT_MODEL_A", "qwen2.5-coder:7b-instruct-q4_K_M"),
        ),
        model_reviewer=os.environ.get(
            "MODEL_REVIEWER",
            os.environ.get("MULTI_AGENT_MODEL_B", "qwen2.5:3b-instruct-q4_K_M"),
        ),
        max_loops=int(os.environ.get("MAX_LOOPS", os.environ.get("MULTI_AGENT_MAX_LOOPS", "3"))),
        delay_sec=float(os.environ.get("DELAY_BETWEEN_CALLS", "2")),
        min_score_regenerate=int(os.environ.get("MIN_SCORE_REGENERATE", "6")),
        stream=os.environ.get("STREAM_OUTPUT", "1").strip() not in ("0", "false", "False"),
        timeout_planner=int(os.environ.get("TIMEOUT_PLANNER_SEC", "120")),
        timeout_coder=int(os.environ.get("TIMEOUT_CODER_SEC", "600")),
        timeout_reviewer=int(os.environ.get("TIMEOUT_REVIEWER_SEC", "180")),
        system_planner=os.environ.get("SYSTEM_PLANNER", ""),
        system_coder=os.environ.get("SYSTEM_CODER", ""),
        system_reviewer=os.environ.get("SYSTEM_REVIEWER", ""),
    )


def _thought(cb: PipelineCallbacks | None, msg: str) -> None:
    if cb and cb.on_thought:
        cb.on_thought(msg)


def _cpu_pause(cfg: MultiAgentConfig, cb: PipelineCallbacks | None) -> None:
    if cfg.delay_sec <= 0:
        return
    _thought(cb, f"CPU pause {cfg.delay_sec}s (keeps RAM stable)...")
    if cb and cb.on_pause:
        cb.on_pause(cfg.delay_sec)
    time.sleep(cfg.delay_sec)


def ask(
    cfg: MultiAgentConfig,
    model: str,
    prompt: str,
    *,
    system: str | None = None,
    role_description: str = "",
    timeout_sec: int = 600,
    callbacks: PipelineCallbacks | None = None,
) -> str:
    _thought(callbacks, f"Contacting {model} — {role_description or 'working'}...")
    if callbacks and callbacks.on_section:
        callbacks.on_section(role_description or model, model)

    payload: dict = {"model": model, "prompt": prompt, "stream": cfg.stream}
    if system:
        payload["system"] = system

    try:
        resp = requests.post(
            cfg.ollama_url,
            json=payload,
            stream=cfg.stream,
            timeout=timeout_sec,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        _thought(callbacks, f"Connection failed: {exc}")
        raise ConnectionError(
            f"Could not reach Ollama at {cfg.ollama_url}. Start Ollama, then run `ollama list`."
        ) from exc

    if not cfg.stream:
        text = str(resp.json().get("response", ""))
        _thought(callbacks, f"{model} finished.")
        return text

    parts: list[str] = []
    for raw in resp.iter_lines():
        if not raw:
            continue
        try:
            chunk = json.loads(raw)
        except json.JSONDecodeError:
            continue
        token = chunk.get("response") or ""
        if token:
            parts.append(token)
            if callbacks and callbacks.on_token:
                callbacks.on_token(token)
        if chunk.get("done"):
            break
    _thought(callbacks, f"{model} finished.")
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


def build_plan(
    cfg: MultiAgentConfig,
    task: str,
    *,
    replan: bool = False,
    callbacks: PipelineCallbacks | None = None,
) -> str:
    label = "Re-planning" if replan else "Planning"
    _thought(callbacks, f"{label}: breaking the task into steps (Planner)...")
    prompt = task
    if replan:
        prompt = (
            "Previous attempt scored too low. Create a NEW plan from scratch.\n\n"
            f"TASK:\n{task}"
        )
    plan = ask(
        cfg,
        cfg.model_planner,
        prompt,
        system=cfg.system_planner,
        role_description="Planner — task decomposition",
        timeout_sec=cfg.timeout_planner,
        callbacks=callbacks,
    )
    if callbacks and callbacks.on_token:
        callbacks.on_token("\n\n")
    return plan


def run_pipeline(
    task: str,
    cfg: MultiAgentConfig | None = None,
    callbacks: PipelineCallbacks | None = None,
) -> PipelineResult:
    cfg = cfg or load_config()
    original_task = task.strip()
    if not original_task:
        raise ValueError("Task is empty")

    plan = build_plan(cfg, original_task, callbacks=callbacks)
    _cpu_pause(cfg, callbacks)

    best_score = -1
    best_output = ""
    current_task = original_task
    iterations = 0

    for i in range(cfg.max_loops):
        iterations = i + 1
        if callbacks and callbacks.on_token:
            callbacks.on_token(f"\n\n{'=' * 40}\n**Iteration {iterations} / {cfg.max_loops}**\n{'=' * 40}\n\n")

        _thought(callbacks, "Coder implements the plan (slowest step on CPU).")
        code_prompt = f"""Use this plan:

{plan}

Original task:
{original_task}

Current focus:
{current_task}
"""
        solution = ask(
            cfg,
            cfg.model_coder,
            code_prompt,
            system=cfg.system_coder,
            role_description="Coder — implementation",
            timeout_sec=cfg.timeout_coder,
            callbacks=callbacks,
        )
        _cpu_pause(cfg, callbacks)

        _thought(callbacks, "Reviewer checks bugs, improvements, and score.")
        review_prompt = f"Review and improve this code:\n\n{solution}"
        feedback = ask(
            cfg,
            cfg.model_reviewer,
            review_prompt,
            system=cfg.system_reviewer,
            role_description="Reviewer — critique + score",
            timeout_sec=cfg.timeout_reviewer,
            callbacks=callbacks,
        )
        _cpu_pause(cfg, callbacks)

        score = parse_score(feedback)
        confidence = parse_confidence(feedback)
        summary = f"\n\n**Score:** {score}/10 · **Confidence:** {confidence}\n"
        if callbacks and callbacks.on_token:
            callbacks.on_token(summary)

        if score > best_score:
            best_score = score
            best_output = extract_revised_code(feedback) or feedback

        if no_bugs_reported(feedback) or score >= 9:
            _thought(callbacks, "High quality — stopping early.")
            break

        if score < cfg.min_score_regenerate:
            _thought(
                callbacks,
                f"Score below {cfg.min_score_regenerate} — re-planning from scratch next round.",
            )
            plan = build_plan(cfg, original_task, replan=True, callbacks=callbacks)
            _cpu_pause(cfg, callbacks)
            current_task = original_task
        else:
            _thought(callbacks, "Feeding reviewer feedback into the next coder round.")
            current_task = f"Improve using this feedback:\n\n{feedback}"

    if callbacks and callbacks.on_token:
        callbacks.on_token(
            f"\n\n{'=' * 40}\n**BEST SOLUTION** (score {best_score}/10)\n{'=' * 40}\n\n"
        )
        callbacks.on_token(best_output or "(none)")

    return PipelineResult(
        best_output=best_output or "(none)",
        best_score=best_score,
        plan=plan,
        iterations=iterations,
    )
