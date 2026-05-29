from ..sources.sportsbook_cache import SportsbookCache
from .sportsbook import SportsbookProfile


class FanDuelProfile(SportsbookProfile):
    platform_key = "fanduel"
    display_name = "FanDuel"

    def __init__(self, config, http, cache: SportsbookCache | None = None):
        super().__init__(config, http, platform_key="fanduel", display_name="FanDuel", cache=cache)
