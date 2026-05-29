from ..sources.sportsbook_cache import SportsbookCache
from .sportsbook import SportsbookProfile


class DraftKingsProfile(SportsbookProfile):
    platform_key = "draftkings"
    display_name = "DraftKings"

    def __init__(self, config, http, cache: SportsbookCache | None = None):
        super().__init__(config, http, platform_key="draftkings", display_name="DraftKings", cache=cache)
