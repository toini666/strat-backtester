"""Campaign-local constants: BEST params + strategy/symbol/period.

Sweeps import these to stay slim.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import bench, run_backtest, summarize, fmt_summary  # noqa: F401
from scripts.goals._shared.engine_settings import make_engine_settings, ui_default_engine_settings  # noqa: F401


STRATEGY = "HMASSLOsciV3"
SYMBOL = "MNQ"
START = "2026-01-06T00:00"
END = "2026-05-13T22:00"

# Best tuned strategy params identified during the campaign
BEST_PARAMS = {
    "cloud_on": True,
    "one_trade_per_entry_window": False,
    "sig_extreme": 22.0,
    "signal_length": 4,
    "entry_window_bars": 4,
}


def bench_v3(label: str, *, interval: str = "3m", strategy_params=None,
             risk_per_trade: float = 0.01, engine_settings=None):
    return bench(
        label,
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=interval,
        start=START,
        end=END,
        strategy_params=strategy_params,
        risk_per_trade=risk_per_trade,
        engine_settings=engine_settings,
    )
