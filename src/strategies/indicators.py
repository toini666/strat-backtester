import pandas as pd


class Indicators:
    """Wrapper that ensures pandas-ta extensions are loaded."""

    @staticmethod
    def ensure_ta_extensions():
        """No-op — pandas-ta patches pandas on import."""
        pass
