"""Emit unified harvester ticks to stdout, files, or localhost WebSocket."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from harvester.models import UnifiedEvent


def events_to_json(events: Iterable[UnifiedEvent], pretty: bool = False) -> str:
    """Serialize unified events as a JSON array."""

    payload = [event.to_jsonable() for event in events]
    return json.dumps(payload, indent=2 if pretty else None, separators=None if pretty else (",", ":"))


def emit_stdout(events: Iterable[UnifiedEvent], pretty: bool = False) -> None:
    """Print a unified JSON tick to stdout."""

    print(events_to_json(events, pretty=pretty))


def emit_file(events: Iterable[UnifiedEvent], path: Path, pretty: bool = False) -> None:
    """Write one unified JSON tick to a file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(events_to_json(events, pretty=pretty) + "\n", encoding="utf-8")


async def emit_local_websocket(events: Iterable[UnifiedEvent], uri: str, pretty: bool = False) -> None:
    """Send one unified JSON tick to a localhost WebSocket server if configured."""

    try:
        import websockets  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("WebSocket output requires installing websockets") from exc

    async with websockets.connect(uri) as websocket:
        await websocket.send(events_to_json(events, pretty=pretty))
