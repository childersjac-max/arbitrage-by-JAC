#!/usr/bin/env python3
"""
Run deploy/UI phase prompts through the 3-agent pipeline unattended.

Usage:
  python run_phases.py --set deploy     # 6 ingest/deploy phases
  python run_phases.py --set ui_card    # 6 UI phases (cards + filters)
  python run_phases.py --set full       # deploy + ui_card (entire pipeline)
  python run_phases.py --list
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from pipeline_core import PipelineCallbacks, load_config, run_pipeline
from project_context import resolve_project_root

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"

AUTONOMOUS_PREFIX = """AUTONOMOUS BATCH MODE — do NOT ask the user to paste terminal output between steps.
Complete this entire phase in one pass. If commands are needed, output ONE bash block at the end.
If code is needed, output COMPLETE file contents (no TODOs). Then stop.

"""

DEPLOY_PHASES: list[tuple[str, str]] = [
    ("01_config_ingest", "llm_deploy_phases/PHASE_1_harvester_config_ingest.txt"),
    ("02_event_markets", "llm_deploy_phases/PHASE_2_event_markets_multisport.txt"),
    ("03_arb_engine", "llm_deploy_phases/PHASE_3_arb_engine_all_lines.txt"),
    ("04_dashboard_lan", "llm_deploy_phases/PHASE_4_dashboard_lan_url.txt"),
    ("05_verify_browser", "llm_deploy_phases/PHASE_5_verify_browser.txt"),
    ("06_always_on", "llm_deploy_phases/PHASE_6_always_on_optional.txt"),
]

UI_CARD_PHASES: list[tuple[str, str]] = [
    ("ui_A_api", "llm_ui_phases/UI_PHASE_A_api_payload.txt"),
    ("ui_B_filters_html", "llm_ui_phases/UI_PHASE_B_filters_panel_html.txt"),
    ("ui_C_card_css", "llm_ui_phases/UI_PHASE_C_card_html_css.txt"),
    ("ui_D_card_js", "llm_ui_phases/UI_PHASE_D_card_js.txt"),
    ("ui_E_filters_js", "llm_ui_phases/UI_PHASE_E_filters_js.txt"),
    ("ui_F_verify", "llm_ui_phases/UI_PHASE_F_verify_polish.txt"),
]

PHASE_SETS: dict[str, list[tuple[str, str]]] = {
    "deploy": DEPLOY_PHASES,
    "ui": [("ui_legacy", "llm_multi_agent_arb_card_dashboard_SHORT.txt")],
    "ui_card": UI_CARD_PHASES,
    "full": DEPLOY_PHASES + UI_CARD_PHASES,
    "all": DEPLOY_PHASES + UI_CARD_PHASES,
}


def _load_prompt(repo: Path, rel: str) -> str:
    path = repo / "prompts" / rel
    if not path.is_file():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def _log_path(phase_id: str) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return LOG_DIR / f"phase_{phase_id}_{ts}.txt"


def run_one_phase(phase_id: str, task: str, *, log_file: Path) -> int:
    cfg = load_config()
    lines: list[str] = []

    def capture_thought(msg: str) -> None:
        line = f"[THOUGHT] {msg}"
        print(line, flush=True)
        lines.append(line)

    def on_section(role: str, model: str) -> None:
        block = f"\n--- {role} ({model}) ---\n"
        print(block, flush=True)
        lines.append(block)

    def on_token(token: str) -> None:
        print(token, end="", flush=True)
        lines.append(token)

    callbacks = PipelineCallbacks(
        on_thought=capture_thought,
        on_section=on_section,
        on_token=on_token,
    )

    print(f"\n{'=' * 60}\nPHASE: {phase_id}\n{'=' * 60}\n", flush=True)
    result = run_pipeline(AUTONOMOUS_PREFIX + task, cfg, callbacks)
    footer = (
        f"\n\n{'=' * 60}\n"
        f"PHASE {phase_id} DONE — score {result.best_score}/10\n"
        f"{'=' * 60}\n"
    )
    print(footer, flush=True)
    lines.append(footer)
    lines.append(result.best_output)

    log_file.write_text("".join(lines), encoding="utf-8")
    print(f"Log saved: {log_file}", flush=True)
    return result.best_score


def main() -> int:
    parser = argparse.ArgumentParser(description="Unattended multi-agent phase runner")
    parser.add_argument(
        "--set",
        choices=list(PHASE_SETS.keys()),
        default="deploy",
        help="deploy | ui_card | full (deploy+ui) | ui (legacy single prompt)",
    )
    parser.add_argument("--from", dest="from_idx", type=int, default=1, metavar="N")
    parser.add_argument("--to", dest="to_idx", type=int, default=99, metavar="N")
    parser.add_argument("--list", action="store_true", help="List phases and exit")
    args = parser.parse_args()

    repo = resolve_project_root()
    phases = PHASE_SETS[args.set]

    if args.list:
        print(f"Repo: {repo}\n")
        for set_name, set_phases in PHASE_SETS.items():
            print(f"Set '{set_name}' ({len(set_phases)} phases):")
            for i, (pid, rel) in enumerate(set_phases, start=1):
                print(f"  {i}. {pid}  →  prompts/{rel}")
            print()
        return 0

    selected = phases[args.from_idx - 1 : args.to_idx]
    if not selected:
        print("No phases in range.", file=sys.stderr)
        return 1

    print(
        f"Unattended run — set={args.set} | phases {args.from_idx}-{min(args.to_idx, len(phases))} of {len(phases)}\n"
        f"Repo: {repo}\nLogs: {LOG_DIR}\n",
        flush=True,
    )

    scores: list[int] = []
    for phase_id, rel in selected:
        try:
            task = _load_prompt(repo, rel)
        except FileNotFoundError as exc:
            print(exc, file=sys.stderr)
            return 1
        log_file = _log_path(phase_id)
        try:
            score = run_one_phase(phase_id, task, log_file=log_file)
            scores.append(score)
        except KeyboardInterrupt:
            print("\nStopped by user.", flush=True)
            return 130
        except Exception as exc:
            print(f"\nPhase {phase_id} failed: {exc}", file=sys.stderr)
            return 1

    print(f"\nAll done. Scores: {scores}", flush=True)
    print(f"Review logs: {LOG_DIR}", flush=True)
    if args.set in ("ui_card", "full", "all"):
        print("Dashboard: http://127.0.0.1:8765", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
