import vectorbt as vbt
import pandas as pd
import numpy as np

# Create dummy data
price = pd.Series([10.0, 11.0, 10.0, 12.0], index=pd.date_range("2023-01-01", periods=4))
entries = pd.Series([True, False, False, False], index=price.index)
exits = pd.Series([False, False, True, False], index=price.index)

# Run portfolio
pf = vbt.Portfolio.from_signals(price, entries, exits)

# Check records_readable columns
print("Columns:", pf.trades.records_readable.columns.tolist())
print(pf.trades.records_readable.head())
