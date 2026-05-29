from .sportsbook import SportsbookProfile


class BetMGMProfile(SportsbookProfile):
    platform_key = "betmgm"
    display_name = "BetMGM"

    def __init__(self, config, http):
        super().__init__(config, http, platform_key="betmgm", display_name="BetMGM")
