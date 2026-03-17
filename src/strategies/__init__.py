from .indicators import Indicators

__all__ = [
    "Indicators",
    "EMABreakOsc",
    "EMA9Scalp",
    "UTBotAlligatorST",
]


def __getattr__(name):
    if name == "EMABreakOsc":
        from .ema_break_osc import EMABreakOsc

        return EMABreakOsc
    if name == "EMA9Scalp":
        from .ema9_scalp import EMA9Scalp

        return EMA9Scalp
    if name == "UTBotAlligatorST":
        from .utbot_alligator_st import UTBotAlligatorST

        return UTBotAlligatorST
    raise AttributeError(name)
