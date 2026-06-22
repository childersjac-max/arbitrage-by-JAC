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

from allocation.balances import balances_snapshot, get_book_balances, save_book_balances
from config import get_settings
from dashboard_service import (
    build_dashboard_payload,
    execute_run,
    get_run_state,
    load_cached_records,
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
    yield


app = FastAPI(title="Live Arbitrage Finder", lifespan=lifespan)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class RunRequest(BaseModel):
    sport_key: str | None = None


class BalancesUpdate(BaseModel):
    balances: dict[str, float] = Field(default_factory=dict)


@app.get("/api/balances")
async def api_balances():
    return balances_snapshot()


@app.put("/api/balances")
async def api_update_balances(body: BalancesUpdate):
    if not body.balances:
        raise HTTPException(400, "balances object required")
    save_book_balances(body.balances)
    return balances_snapshot()


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
    payload["api_key_configured"] = settings.odds_source_configured()
    payload["odds_provider"] = settings.effective_odds_provider()
    payload["odds_gateway"] = settings.odds_gateway_label()
    return payload


@app.post("/api/run")
async def api_run(body: RunRequest = RunRequest()):
    settings = get_settings()
    if not settings.odds_source_configured():
        provider = settings.effective_odds_provider()
        key_name = "PERPLEXITY_API_KEY" if provider == "perplexity" else "ODDS_API_KEY"
        raise HTTPException(
            400,
            f"{key_name} is not set. Add it to harvester/.env",
        )
    state = get_run_state()
    if state.running:
        return {"ok": True, "running": True, "message": "Run already in progress"}

    sport = body.sport_key if body else None

    async def _background() -> None:
        try:
            await execute_run(sport_key=sport)
        except Exception:
            logger.exception("Background run failed")

    asyncio.create_task(_background())
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
    print("=" * 60)
    print("  HARVESTER ARBITRAGE DASHBOARD (FastAPI)")
    print(f"  Open: http://{host}:{port}")
    print("  For Ollama CHAT use: cd ../local-llm && python web_app.py  →  :7860")
    print("=" * 60)
    uvicorn.run(
        "web_app:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
