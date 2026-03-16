from .base import DataProvider

__all__ = ["DataProvider", "TopStepXProvider", "YFinanceProvider"]


def __getattr__(name):
    if name == "TopStepXProvider":
        from .topstepx import TopStepXProvider

        return TopStepXProvider
    if name == "YFinanceProvider":
        from .yfinance_provider import YFinanceProvider

        return YFinanceProvider
    raise AttributeError(name)
