"""
Multi-phase pipeline so local 8B models can handle large architecture prompts.

Phase 1: JSON plan only (small, structured).
Phase 2..N: One deliverable per phase (config, models, integrator, etc.).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from config import get_settings
from ollama_connect import ollama_chat_completion, resolve_ollama
from paths import PACKAGE_DIR
logger = logging.getLogger(__name__)

ARCHITECT_SYSTEM_FILE = "prompts/system_8b_architect.txt"


@dataclass
class PhaseResult:
    step: int
    title: str
    content: str
    latency_ms: float = 0.0


@dataclass
class ArchitectResult:
    plan_json: dict
    phases: list[PhaseResult] = field(default_factory=list)
    raw_plan_response: str = ""


def _load_architect_system() -> str:
    path = PACKAGE_DIR / ARCHITECT_SYSTEM_FILE
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return "You are a Python architect. Output JSON plans then one file per step."


def _extract_json_object(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("No JSON object in model output")
    return json.loads(stripped[start : end + 1])


def _compress_mega_prompt(mega: str, max_chars: int = 6000) -> str:
    """Trim very long prompts while keeping structure headings."""
    mega = mega.strip()
    if len(mega) <= max_chars:
        return mega
    return mega[: max_chars - 80] + "\n\n[...truncated for 8B context; full text stored in data/last_mega_prompt.txt]"


def _save_mega_prompt(mega: str) -> Path:
    data_dir = PACKAGE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "last_mega_prompt.txt"
    path.write_text(mega, encoding="utf-8")
    return path


async def _architect_chat(user: str, *, json_mode: bool = False, max_tokens: int | None = None) -> str:
    settings = get_settings()
    tokens = max_tokens or settings.architect_phase_max_tokens
    messages = [
        {"role": "system", "content": _load_architect_system()},
        {"role": "user", "content": user},
    ]
    await resolve_ollama()
    from ollama_connect import get_effective_ollama_model

    model = await get_effective_ollama_model()
    return await ollama_chat_completion(
        messages,
        model=model,
        temperature=settings.architect_temperature,
        max_tokens=tokens,
        json_mode=json_mode,
    )


async def run_architect(
    mega_prompt: str,
    *,
    max_phases: int | None = None,
) -> ArchitectResult:
    """
    Turn a large project prompt into a plan + phased implementation snippets.
    """
    import time

    settings = get_settings()
    cap = max_phases if max_phases is not None else settings.architect_max_phases
    full_mega = mega_prompt.strip()
    _save_mega_prompt(full_mega)
    brief = _compress_mega_prompt(full_mega)

    plan_user = (
        "USER MEGA-PROMPT (summarize into a build plan):\n\n"
        f"{brief}\n\n"
        "Respond with ONLY a JSON object matching this schema:\n"
        '{"assumptions":["Git Bash","venv","Ollama localhost","The Odds API key in env"],'
        '"phases":[{"step":1,"title":"short title","files":["relative/path.py"],'
        '"goal":"what this step implements"}]}\n'
        f"Use at most {cap} phases. "
        "Phase 1 must be config+models, include odds_api integrator early, "
        "normalization bridge to local-llm, engine last. "
        "No stealth scraping steps."
    )

    t0 = time.perf_counter()
    raw_plan = await _architect_chat(plan_user, json_mode=True, max_tokens=settings.architect_plan_max_tokens)
    plan_ms = (time.perf_counter() - t0) * 1000

    try:
        plan = _extract_json_object(raw_plan)
    except (json.JSONDecodeError, ValueError) as exc:
        repair = (
            f"Your output was invalid ({exc}). Return ONLY valid JSON with keys "
            '"assumptions" and "phases". No markdown.'
        )
        raw_plan = await _architect_chat(repair + "\n\nBroken output:\n" + raw_plan[:1500], json_mode=True)
        plan = _extract_json_object(raw_plan)

    phases_spec = plan.get("phases") or []
    if not isinstance(phases_spec, list):
        phases_spec = []

    results: list[PhaseResult] = []
    plan_summary = json.dumps(plan, indent=2)[:4000]

    for i, spec in enumerate(phases_spec[:cap]):
        if not isinstance(spec, dict):
            continue
        step = int(spec.get("step") or i + 1)
        title = str(spec.get("title") or f"Phase {step}")
        files = spec.get("files") or []
        goal = str(spec.get("goal") or title)
        file_hint = ", ".join(str(f) for f in files) if files else "see title"

        impl_user = (
            f"MASTER PLAN:\n{plan_summary}\n\n"
            f"Implement PHASE {step} only: {title}\n"
            f"Goal: {goal}\n"
            f"Files to create/edit: {file_hint}\n\n"
            "Environment: Windows, Git Bash, Python 3.11+, project root `harvester/`.\n"
            "Output: complete Python for this phase only. Brief file path comment at top of each file. "
            "No other phases. No markdown fences around the whole answer (code blocks per file OK)."
        )

        t1 = time.perf_counter()
        try:
            content = await _architect_chat(impl_user, json_mode=False)
        except Exception as exc:
            content = f"# Phase {step} failed: {exc}"
        results.append(
            PhaseResult(
                step=step,
                title=title,
                content=content,
                latency_ms=(time.perf_counter() - t1) * 1000,
            )
        )

    return ArchitectResult(plan_json=plan, phases=results, raw_plan_response=raw_plan)
