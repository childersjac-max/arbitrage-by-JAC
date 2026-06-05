#!/usr/bin/env python3
"""
Optional: extract Python from Architect phase markdown into harvester/_promoted/.

Use when you want to diff LLM output against the canonical package in harvester/.
Does not overwrite production modules automatically.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_HARVESTER = Path(__file__).resolve().parents[1]
if str(_HARVESTER) not in sys.path:
    sys.path.insert(0, str(_HARVESTER))

from paths import GENERATED_DIR


def _latest_generated_dir() -> Path | None:
    if not GENERATED_DIR.is_dir():
        return None
    candidates = [p for p in GENERATED_DIR.iterdir() if p.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.name)


def _extract_code_blocks(text: str) -> list[str]:
    pattern = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
    return [m.group(1).strip() for m in pattern.finditer(text) if m.group(1).strip()]


def promote(source_dir: Path | None = None, *, dest_root: Path | None = None) -> Path:
    src = source_dir or _latest_generated_dir()
    if src is None or not src.is_dir():
        raise FileNotFoundError(
            f"No generated folder under {GENERATED_DIR}. Run Architect first."
        )

    out = dest_root or (_HARVESTER / "_promoted" / src.name)
    out.mkdir(parents=True, exist_ok=True)

    plan_path = src / "plan.json"
    if plan_path.is_file():
        (out / "plan.json").write_text(plan_path.read_text(encoding="utf-8"), encoding="utf-8")

    index: list[dict[str, str]] = []
    for md_path in sorted(src.glob("phase_*.md")):
        body = md_path.read_text(encoding="utf-8")
        blocks = _extract_code_blocks(body)
        if not blocks:
            blocks = [body.split("\n", 1)[-1].strip()] if body.strip() else []

        for i, block in enumerate(blocks):
            suffix = f"_{i+1}" if len(blocks) > 1 else ""
            py_name = md_path.stem + suffix + ".py"
            (out / py_name).write_text(block + "\n", encoding="utf-8")
            index.append({"from": md_path.name, "to": py_name})

    (out / "INDEX.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    readme = [
        "Promoted from Architect generated output (reference only).",
        f"Source: {src}",
        f"Files: {len(index)}",
        "",
        "The canonical runnable package is the parent harvester/ tree",
        "(config.py, engine.py, integrators/, normalization/).",
        "Compare _promoted/ with those files and merge ideas manually.",
    ]
    (out / "README.txt").write_text("\n".join(readme), encoding="utf-8")
    return out


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Extract code from harvester/generated/")
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Generated folder (default: newest under harvester/generated/)",
    )
    args = parser.parse_args()
    try:
        out = promote(args.source)
    except FileNotFoundError as exc:
        print(exc)
        return 1
    print(f"Promoted to: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
