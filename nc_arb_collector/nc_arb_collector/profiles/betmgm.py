from ..sources.sportsbook_cache import SportsbookCache
from .sportsbook import SportsbookProfile


class BetMGMProfile(SportsbookProfile):
    platform_key = "betmgm"
    display_name = "BetMGM"

    def __init__(self, config, http, cache: SportsbookCache | None = None):
        super().__init__(config, http, platform_key="betmgm", display_name="BetMGM", cache=cache)
