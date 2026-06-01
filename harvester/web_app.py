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
    execute_run,
    get_run_state,
    load_cached_records,
)

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    cached = load_cached_records()
    state = get_run_state()
    if cached:
        state.records = cached
    yield


app = FastAPI(title="Live Arbitrage Finder", lifespan=lifespan)

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

    async def _background() -> None:
        try:
            await execute_run(sport_key=sport)
        except Exception:
            pass

    asyncio.create_task(_background())
    return {"ok": True, "running": True, "message": "Run started"}


def main() -> None:
    import uvicorn

    settings = get_settings()
    host = settings.harvester_ui_host
    port = settings.harvester_ui_port
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    uvicorn.run(
        "web_app:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
