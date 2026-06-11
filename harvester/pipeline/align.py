"""Canonical alignment via local Ollama."""

from __future__ import annotations

from models_depth import EventSnapshot
from fuzzy_normalizer import build_canonical_reference, map_entities_to_canonical


async def align_events(
  events: list[EventSnapshot],
  *,
  use_ollama: bool = True,
) -> list[EventSnapshot]:
  if not use_ollama:
    return events

  fragments: list[str] = []
  for ev in events:
    fragments.extend([ev.home_team, ev.away_team, ev.normalized_event_name])
    for line in ev.lines:
      fragments.append(line.selection_name)

  fragments = sorted({f.strip() for f in fragments if f and f.strip()})
  if not fragments:
    return events

  ref = build_canonical_reference(*fragments)
  try:
    mapping = await map_entities_to_canonical(fragments, ref)
  except Exception:
    return events

  for ev in events:
    home = mapping.get(ev.home_team) or ev.home_team
    away = mapping.get(ev.away_team) or ev.away_team
    if home and away:
      ev.normalized_event_name = f"{away} @ {home}"
    for line in ev.lines:
      hit = mapping.get(line.selection_name)
      if hit:
        line.selection_name = hit

  return events
