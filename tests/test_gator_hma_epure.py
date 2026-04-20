import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.strategies.gator_hma_epure import GatorHMAEpure


def test_gator_occ_non_repaint_updates_only_after_completed_group():
    index = pd.date_range("2024-01-01 09:00", periods=7, freq="5min", tz="Europe/Brussels")
    open_ = pd.Series([10, 11, 12, 13, 14, 15, 16], index=index, dtype=float)
    close = pd.Series([20, 21, 22, 23, 24, 25, 26], index=index, dtype=float)

    close_alt, open_alt = GatorHMAEpure._compute_occ_non_repaint(
        open_,
        close,
        basis_len=1,
        factor=3,
    )

    expected_close = pd.Series([np.nan, np.nan, 22.0, 22.0, 22.0, 25.0, 25.0], index=index)
    expected_open = pd.Series([np.nan, np.nan, 10.0, 10.0, 10.0, 13.0, 13.0], index=index)

    pd.testing.assert_series_equal(close_alt, expected_close, check_names=False)
    pd.testing.assert_series_equal(open_alt, expected_open, check_names=False)


def test_gator_hma_epure_uses_single_full_tp1():
    strategy = GatorHMAEpure()
    settings = strategy.get_simulator_settings({"cooldown_bars": 2})

    assert settings["tp1_execution_mode"] == "touch"
    assert settings["tp1_full_exit"] is True
    assert settings["tp1_partial_pct"] == 1.0
    assert settings["tp2_partial_pct"] == 0.0
    assert settings["cooldown_bars"] == 2
