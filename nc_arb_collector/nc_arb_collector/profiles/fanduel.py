from .sportsbook import SportsbookProfile


class FanDuelProfile(SportsbookProfile):
    platform_key = "fanduel"
    display_name = "FanDuel"

    def __init__(self, config, http):
        super().__init__(config, http, platform_key="fanduel", display_name="FanDuel")
