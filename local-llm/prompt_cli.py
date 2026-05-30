#!/usr/bin/env python3
"""
Interactive and one-shot prompting for your local LLM.

Examples:
  python prompt_cli.py "Explain Python asyncio in 3 bullets"
  python prompt_cli.py --file prompts/example.txt
  python prompt_cli.py --interactive
  python prompt_cli.py --stream "Write a hello-world scraper skeleton"
  python prompt_cli.py --system "You are a Python expert" "Review this code: ..."
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from local_inference import LocalInferenceClient
from prompt_types import ChatMessage


def _read_prompt_file(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _read_system_file(path: Path | None) -> str | None:
    if path is None:
        return None
    return path.read_text(encoding="utf-8").strip()


async def _run_once(args: argparse.Namespace) -> int:
    prompt = args.prompt
    if args.file:
        prompt = _read_prompt_file(Path(args.file))
    if not prompt:
        print("Error: provide a prompt argument or --file", file=sys.stderr)
        return 1

    system = args.system
    if args.system_file:
        system = _read_system_file(Path(args.system_file))

    async with LocalInferenceClient() as client:
        if args.stream:

            def on_token(t: str) -> None:
                print(t, end="", flush=True)

            result = await client.complete(
                prompt,
                system=system,
                json_mode=args.json,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                stream=True,
                on_token=on_token,
            )
            print()
            if args.verbose:
                print(f"\n[{result.latency_ms:.0f} ms | {result.model}]", file=sys.stderr)
        else:
            result = await client.complete(
                prompt,
                system=system,
                json_mode=args.json,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            )
            print(result.content)
            if args.verbose:
                print(f"[{result.latency_ms:.0f} ms | {result.model}]", file=sys.stderr)
    return 0


async def _run_interactive(args: argparse.Namespace) -> int:
    system = args.system
    if args.system_file:
        system = _read_system_file(Path(args.system_file))

    history: list[ChatMessage] = []
    if system:
        history.append(ChatMessage("system", system))
    print("Local LLM chat (empty line or Ctrl+C to exit)")
    print("Commands: /clear  /save <file>  /stream on|off")
    stream = args.stream

    async with LocalInferenceClient() as client:
        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                break

            if not user_input:
                continue
            if user_input == "/clear":
                history = [m for m in history if m.role == "system"]
                print("History cleared.")
                continue
            if user_input.startswith("/stream "):
                stream = user_input.split(maxsplit=1)[1].lower() in ("on", "true", "1")
                print(f"Streaming: {stream}")
                continue
            if user_input.startswith("/save "):
                out = Path(user_input.split(maxsplit=1)[1])
                out.write_text(
                    "\n".join(f"{m.role}: {m.content}" for m in history),
                    encoding="utf-8",
                )
                print(f"Saved to {out}")
                continue

            history.append(ChatMessage("user", user_input))

            if stream:

                def on_token(t: str) -> None:
                    print(t, end="", flush=True)

                print("Assistant: ", end="", flush=True)
                result = await client.chat(
                    history,
                    json_mode=args.json,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    stream=True,
                    on_token=on_token,
                )
                print()
            else:
                result = await client.chat(
                    history,
                    json_mode=args.json,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                )
                print(f"Assistant: {result.content}")

            history.append(ChatMessage("assistant", result.content))
            if args.verbose:
                print(f"  [{result.latency_ms:.0f} ms]", file=sys.stderr)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Prompt your local Ollama/vLLM")
    parser.add_argument("prompt", nargs="?", default="", help="Your prompt text")
    parser.add_argument("-f", "--file", help="Read prompt from a text file")
    parser.add_argument("-i", "--interactive", action="store_true", help="Multi-turn chat loop")
    parser.add_argument("-s", "--system", help="Custom system message")
    parser.add_argument("--system-file", help="Read system message from file")
    parser.add_argument("--json", action="store_true", help="Force JSON output format")
    parser.add_argument("--stream", action="store_true", help="Stream tokens as they generate")
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("-v", "--verbose", action="store_true", help="Print latency to stderr")
    args = parser.parse_args()

    if args.interactive:
        return asyncio.run(_run_interactive(args))
    return asyncio.run(_run_once(args))


if __name__ == "__main__":
    sys.exit(main())
