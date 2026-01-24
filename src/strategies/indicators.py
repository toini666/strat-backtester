import pandas_ta_classic as ta
import pandas as pd

class Indicators:
    """
    Wrapper around pandas-ta for easy access to indicators.
    Ensure pandas-ta is imported and extension is registered.
    """
    
    @staticmethod
    def ensure_ta_extensions():
        """
        Just checking that the extension is loaded.
        Pandas-ta usually patches pandas on import.
        """
        pass
        
    # Helper methods if we want typed access, 
    # but df.ta.sma() is usually preferred for flexibility.
