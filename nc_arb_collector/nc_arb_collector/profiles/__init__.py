from .base import ExtractionProfile
from .betmgm import BetMGMProfile
from .draftkings import DraftKingsProfile
from .fanduel import FanDuelProfile
from .kalshi import KalshiProfile
from .prediction_markets import PredictionMarketsProfile

NC_PROFILES = (
    DraftKingsProfile,
    FanDuelProfile,
    BetMGMProfile,
    KalshiProfile,
    PredictionMarketsProfile,
)

__all__ = [
    "ExtractionProfile",
    "DraftKingsProfile",
    "FanDuelProfile",
    "BetMGMProfile",
    "KalshiProfile",
    "PredictionMarketsProfile",
    "NC_PROFILES",
]
