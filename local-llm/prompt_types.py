"""Types for free-form prompting (separate from normalization)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Role = Literal["system", "user", "assistant"]


@dataclass
class ChatMessage:
    role: Role
    content: str

    def to_api_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class PromptResult:
    content: str
    model: str
    latency_ms: float
    backend: str
