"""Gradio version differences (theme/css on Blocks vs launch)."""

from __future__ import annotations

import inspect
from typing import Any

import gradio as gr


def blocks_constructor_kwargs(*, title: str, theme: Any, css: str) -> dict[str, Any]:
    """Keyword args safe for gr.Blocks() on this Gradio install."""
    kw: dict[str, Any] = {"title": title}
    sig = inspect.signature(gr.Blocks.__init__)
    if "theme" in sig.parameters:
        kw["theme"] = theme
    if "css" in sig.parameters:
        kw["css"] = css
    return kw


def styling_for_launch(*, theme: Any, css: str) -> dict[str, Any]:
    """If Blocks() cannot take theme/css, pass them to launch() instead."""
    kw: dict[str, Any] = {}
    blocks_sig = inspect.signature(gr.Blocks.__init__)
    launch_sig = inspect.signature(gr.Blocks.launch)
    if "theme" not in blocks_sig.parameters and "theme" in launch_sig.parameters:
        kw["theme"] = theme
    if "css" not in blocks_sig.parameters and "css" in launch_sig.parameters:
        kw["css"] = css
    return kw


def filter_launch_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Drop kwargs this Gradio version's launch() does not accept."""
    allowed = set(inspect.signature(gr.Blocks.launch).parameters) - {"self"}
    return {k: v for k, v in kwargs.items() if k in allowed}
