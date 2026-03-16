from .indicators import Indicators

__all__ = [
    "Indicators",
    "UTBotHeikin",
    "BullesBollinger",
    "DeltaDiv",
    "EMA9Retest",
    "UTBotSTC",
    "UTBotOCC",
]


def __getattr__(name):
    if name == "UTBotHeikin":
        from .utbot_heikin import UTBotHeikin

        return UTBotHeikin
    if name == "BullesBollinger":
        from .bulles_bollinger import BullesBollinger

        return BullesBollinger
    if name == "DeltaDiv":
        from .delta_div import DeltaDiv

        return DeltaDiv
    if name == "EMA9Retest":
        from .ema9_retest import EMA9Retest

        return EMA9Retest
    if name == "UTBotSTC":
        from .utbot_stc import UTBotSTC

        return UTBotSTC
    if name == "UTBotOCC":
        from .utbot_occ import UTBotOCC

        return UTBotOCC
    raise AttributeError(name)
