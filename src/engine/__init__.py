__all__ = ["Backtester"]


def __getattr__(name):
    if name == "Backtester":
        from .backtester import Backtester

        return Backtester
    raise AttributeError(name)
