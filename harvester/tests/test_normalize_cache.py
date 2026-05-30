"""Tests for normalization cache behavior."""

from pathlib import Path

import pytest

from harvester.config import HarvesterSettings
from harvester.normalize.bridge import LocalLLMNormalizationBridge
from harvester.normalize.reference_loader import ReferenceData


class CountingClient:
    """Fake local inference client that records calls."""

    def __init__(self) -> None:
        self.calls = 0

    async def normalize_batch(self, fragments: list[str], temperature: float = 0) -> dict[str, str]:
        """Return upper-case normalizations for uncached fragments."""

        self.calls += 1
        assert temperature == 0
        return {fragment: fragment.upper() for fragment in fragments}


def settings(cache_path: Path) -> HarvesterSettings:
    """Build isolated test settings."""

    return HarvesterSettings(
        THE_ODDS_API_KEY="test",
        HARVESTER_NORMALIZE_CACHE_PATH=str(cache_path),
        LOCAL_LLM_BATCH_SIZE=20,
    )


@pytest.mark.asyncio
async def test_normalize_cache_avoids_repeat_inference(tmp_path: Path) -> None:
    """Second normalization run should use sqlite cache."""

    client = CountingClient()
    bridge = LocalLLMNormalizationBridge(
        settings=settings(tmp_path / "cache.sqlite3"),
        reference_data=ReferenceData(),
        client=client,
    )

    first = await bridge.normalize_batch(["bos celtics"])
    second = await bridge.normalize_batch(["bos celtics"])

    assert first == {"bos celtics": "BOS CELTICS"}
    assert second == first
    assert client.calls == 1


@pytest.mark.asyncio
async def test_alias_table_fallback_does_not_call_llm(tmp_path: Path) -> None:
    """Alias matches resolve before local inference."""

    client = CountingClient()
    bridge = LocalLLMNormalizationBridge(
        settings=settings(tmp_path / "cache.sqlite3"),
        reference_data=ReferenceData(aliases={"BOS": "Boston Celtics"}),
        client=client,
    )

    result = await bridge.normalize_batch(["BOS"])

    assert result == {"BOS": "Boston Celtics"}
    assert client.calls == 0
