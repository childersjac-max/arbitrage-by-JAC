from .base import ExtractionProfile
from .betmgm import BetMGMProfile
from .draftkings import DraftKingsProfile
from .fanduel import FanDuelProfile
from .kalshi import KalshiProfile
from .prediction_markets import PredictionMarketsProfile

# Built in orchestrator with shared SportsbookCache — do not instantiate tuple directly.
NC_PROFILE_CLASSES = (
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
    "NC_PROFILE_CLASSES",
]
