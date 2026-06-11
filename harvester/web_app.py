#!/usr/bin/env python3
"""Live Arbitrage Finder — web dashboard to run harvester and view results."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import get_settings
from dashboard_service import (
    build_dashboard_payload,
    execute_run_tracked,
    get_run_state,
    load_cached_records,
    maybe_reset_stale_run,
    reset_run_state,
)

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    reset_run_state()
    cached = load_cached_records()
    state = get_run_state()
    if cached:
        state.records = cached
        if not state.source_report and cached:
            from source_status import build_source_report

            state.source_report = build_source_report(cached)
    yield


app = FastAPI(title="Live Arbitrage Finder", lifespan=lifespan)


def _static_file(name: str, media_type: str) -> FileResponse:
    path = STATIC_DIR / name
    if not path.is_file():
        raise HTTPException(404, f"Static asset not found: {name}")
    return FileResponse(path, media_type=media_type)


@app.get("/static/styles.css")
async def static_styles() -> FileResponse:
    return _static_file("styles.css", "text/css")


@app.get("/static/app.js")
async def static_app_js() -> FileResponse:
    return _static_file("app.js", "application/javascript")


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class RunRequest(BaseModel):
    sport_key: str | None = None


@app.get("/")
async def index() -> FileResponse:
    index_path = STATIC_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(404, "Dashboard UI not found")
    return FileResponse(index_path)


@app.get("/api/status")
async def api_status(day: str = Query("today", pattern="^(today|tomorrow)$")):
    maybe_reset_stale_run()
    state = get_run_state()
    records = state.records
    if not records:
        records = load_cached_records()
        state.records = records
    payload = build_dashboard_payload(records, day=day)
    settings = get_settings()
    payload["api_key_configured"] = bool(settings.odds_api_key)
    return payload


@app.post("/api/run")
async def api_run(body: RunRequest = RunRequest()):
    settings = get_settings()
    if not settings.odds_api_key:
        raise HTTPException(
            400,
            "ODDS_API_KEY is not set. Add it to harvester/.env",
        )
    state = get_run_state()
    if state.running:
        return {"ok": True, "running": True, "message": "Run already in progress"}

    sport = body.sport_key if body else None

    import dashboard_service as dash

    if dash._active_run_task is not None and not dash._active_run_task.done():
        return {"ok": True, "running": True, "message": "Run already in progress"}

    async def _background() -> None:
        try:
            await execute_run_tracked(sport_key=sport)
        except asyncio.CancelledError:
            logger.info("Background run task cancelled")
        except Exception:
            logger.exception("Background run failed")

    dash._active_run_task = asyncio.create_task(_background())
    return {"ok": True, "running": True, "message": "Run started"}


@app.post("/api/reset-run")
async def api_reset_run():
    """Force-clear stuck Running state."""
    reset_run_state()
    return {"ok": True, "running": False}


def main() -> None:
    import uvicorn

    settings = get_settings()
    host = settings.harvester_ui_host
    port = settings.harvester_ui_port
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    css_ok = (STATIC_DIR / "styles.css").is_file()
    js_ok = (STATIC_DIR / "app.js").is_file()
    print("=" * 60)
    print("  HARVESTER ARBITRAGE DASHBOARD (FastAPI)")
    print(f"  Open: http://{host}:{port}")
    print(f"  Static: {STATIC_DIR}  css={'OK' if css_ok else 'MISSING'}  js={'OK' if js_ok else 'MISSING'}")
    print("  For Ollama CHAT use: cd ../local-llm && python web_app.py  →  :7860")
    print("=" * 60)
    if not css_ok:
        logging.warning("styles.css missing — dashboard will look unstyled")
    uvicorn.run(
        "web_app:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
