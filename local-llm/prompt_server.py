#!/usr/bin/env python3
"""
Localhost HTTP API for free-form prompting.

POST http://127.0.0.1:5050/prompt
Content-Type: application/json

{
  "prompt": "Your question here",
  "system": "optional system message",
  "json_mode": false,
  "stream": false,
  "temperature": 0.7,
  "max_tokens": 4096
}

GET http://127.0.0.1:5050/health
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from config import get_settings
from local_inference import LocalInferenceClient

logger = logging.getLogger(__name__)

_client: LocalInferenceClient | None = None
_loop: asyncio.AbstractEventLoop | None = None


def _run_async(coro: Any) -> Any:
    global _loop
    if _loop is None:
        _loop = asyncio.new_event_loop()
    return _loop.run_until_complete(coro)


class PromptHandler(BaseHTTPRequestHandler):
    server_version = "LocalLLMPrompt/1.0"

    def log_message(self, format: str, *args: object) -> None:
        logger.info("%s - %s", self.address_string(), format % args)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            try:
                assert _client is not None
                health = _run_async(_client.health_check())
                self._send_json(200, {"status": "ok", **health})
            except Exception as exc:
                self._send_json(503, {"status": "error", "detail": str(exc)})
            return
        self._send_json(404, {"error": "not found", "paths": ["GET /health", "POST /prompt"]})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/prompt":
            self._send_json(404, {"error": "use POST /prompt"})
            return

        try:
            body = self._read_json_body()
        except json.JSONDecodeError as exc:
            self._send_json(400, {"error": f"invalid json: {exc}"})
            return

        prompt = body.get("prompt", "").strip()
        if not prompt:
            self._send_json(400, {"error": "missing field: prompt"})
            return

        assert _client is not None
        try:
            result = _run_async(
                _client.complete(
                    prompt,
                    system=body.get("system"),
                    json_mode=bool(body.get("json_mode", False)),
                    temperature=body.get("temperature"),
                    max_tokens=body.get("max_tokens"),
                    stream=bool(body.get("stream", False)),
                )
            )
            self._send_json(
                200,
                {
                    "content": result.content,
                    "model": result.model,
                    "latency_ms": result.latency_ms,
                    "backend": result.backend,
                },
            )
        except Exception as exc:
            logger.exception("prompt failed")
            self._send_json(500, {"error": str(exc)})


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=settings.local_llm_prompt_server_host)
    parser.add_argument("--port", type=int, default=settings.local_llm_prompt_server_port)
    args = parser.parse_args()

    global _client
    _client = LocalInferenceClient()
    _run_async(_client.start())

    server = ThreadingHTTPServer((args.host, args.port), PromptHandler)
    print(f"Prompt server listening on http://{args.host}:{args.port}")
    print("  POST /prompt  — send JSON { \"prompt\": \"...\" }")
    print("  GET  /health  — check Ollama/vLLM connectivity")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        _run_async(_client.close())
        server.server_close()


if __name__ == "__main__":
    main()
