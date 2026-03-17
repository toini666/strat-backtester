"""
EMA9 Momentum Retest (Scalp) strategy — simulator-based.

Translated from PineScript indicator EMA9-scalp.txt.
Uses a state machine for setup detection, retest confirmation, and breakout entry.

Entry: N consecutive bullish/bearish candles above/below EMA with first candle
       touching EMA, then price retests EMA within tolerance, then breakout
       above previous high (long) or below previous low (short).
Exit: Stop loss, TP1 partial (RR-based or fixed points, at bar close when touched),
      breakeven at separate BE level, EMA cross exit after TP1.
"""

from .base import Strategy
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
from typing import Dict, Any


class EMA9Scalp(Strategy):
    """EMA9 Momentum Retest — scalp entries on EMA retest breakout."""

    name = "EMA9Scalp"
    manual_exit = True
    use_simulator = True
    simulator_settings = {
        "tp1_execution_mode": "bar_close_if_touched",
        "ema_exit_after_tp1_only": True,
    }

    default_params = {
        # Indicator
        "ema_length": 7,

        # Setup
        "nb_candles": 3,
        "setup_bar_can_retest": False,
        "retest_tolerance": 1,       # ticks
        "max_bars": 10,

        # Position / Risk
        "sl_margin": 3,              # ticks
        "max_stop_points": 60.0,     # max SL distance in points
        "rr_be": 1.0,               # R:R to move SL to breakeven
        "rr_tp1": 2.0,              # R:R for TP1
        "tp1_points": 50.0,         # fixed TP1 distance in points (0 = disabled)
        "tp1_partial_pct": 0.50,    # 50% of position closed at TP1
        "tp2_partial_pct": 0.0,     # no TP2

        # Injected by engine
        "tick_size": 0.25,
    }

    param_ranges = {
        "ema_length": [5, 7, 9, 13],
        "nb_candles": [2, 3, 4, 5],
        "retest_tolerance": [0, 1, 2, 3],
        "max_bars": [5, 10, 15, 20],
        "sl_margin": [0, 2, 3, 5],
        "max_stop_points": [30.0, 40.0, 50.0, 60.0],
        "rr_be": [0.5, 1.0, 1.5],
        "rr_tp1": [1.5, 2.0, 2.5, 3.0],
        "tp1_points": [0.0, 30.0, 50.0, 70.0],
        "tp1_partial_pct": [0.3, 0.5, 0.7],
    }

    def get_simulator_settings(self, params=None):
        p = self.get_params(params)
        settings = self.simulator_settings.copy()
        settings["tp1_partial_pct"] = p.get("tp1_partial_pct", 0.50)
        settings["tp2_partial_pct"] = p.get("tp2_partial_pct", 0.0)
        return settings

    # ------------------------------------------------------------------
    # Main signal generation
    # ------------------------------------------------------------------

    def generate_signals(
        self, data: pd.DataFrame, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run the full PineScript state machine to detect entries.

        The state machine tracks both setup/entry states (0,1,2,5,6) and
        position states (3,4,7,8,9,10) at the bar level. This ensures
        entry timing matches PineScript exactly — setups are blocked while
        a position is active, just as in TradingView.

        The simulator then re-executes position management with intra-bar
        resolution for more accurate exit pricing.
        """
        p = self.get_params(params)

        ema_len = p["ema_length"]
        nb_candles = p["nb_candles"]
        setup_bar_can_retest = p["setup_bar_can_retest"]
        retest_tol_ticks = p["retest_tolerance"]
        max_bars = p["max_bars"]
        sl_margin = p["sl_margin"]
        max_stop_pts = p["max_stop_points"]
        rr_be = p["rr_be"]
        rr_tp1 = p["rr_tp1"]
        tp1_points = p["tp1_points"]
        tick_size = p["tick_size"]

        close = data["Close"]
        open_ = data["Open"]
        high = data["High"]
        low = data["Low"]
        n = len(data)

        # --- EMA ---
        ema = ta.ema(close, length=ema_len)

        # --- Numpy arrays ---
        np_close = close.values
        np_open = open_.values
        np_high = high.values
        np_low = low.values
        np_ema = ema.values

        tol_price = retest_tol_ticks * tick_size

        def round_tick(price):
            if tick_size > 0:
                return round(price / tick_size) * tick_size
            return price

        def get_tp1_long(entry, risk):
            rr_target = entry + risk * rr_tp1
            if tp1_points > 0:
                fixed_target = entry + tp1_points
                return round_tick(min(rr_target, fixed_target))
            return round_tick(rr_target)

        def get_tp1_short(entry, risk):
            rr_target = entry - risk * rr_tp1
            if tp1_points > 0:
                fixed_target = entry - tp1_points
                return round_tick(max(rr_target, fixed_target))
            return round_tick(rr_target)

        # --- Output arrays ---
        long_entries = np.zeros(n, dtype=bool)
        short_entries = np.zeros(n, dtype=bool)
        sl_long_arr = np.full(n, np.nan)
        sl_short_arr = np.full(n, np.nan)
        tp1_long_arr = np.full(n, np.nan)
        tp1_short_arr = np.full(n, np.nan)
        be_long_arr = np.full(n, np.nan)
        be_short_arr = np.full(n, np.nan)

        # --- Debug arrays ---
        state_arr = np.zeros(n, dtype=int)

        # --- State machine ---
        trade_state = 0
        setup_bar = -1
        ready_bar = -1  # bar where retest confirmed (for entry delay)
        entry_bar = -1
        # Position tracking at bar level (mirrors PineScript for entry blocking)
        entry_price = np.nan
        sl_price = np.nan
        tp1_price = np.nan
        be_level = np.nan

        start_bar = max(ema_len + 2, nb_candles + 1)

        for i in range(start_bar, n):
            if np.isnan(np_ema[i]):
                state_arr[i] = trade_state
                continue

            # ============================================
            # SETUP DETECTION (computed every bar)
            # ============================================
            # Long setup: N consecutive bullish candles closing above EMA
            long_setup_ok = True
            for k in range(nb_candles):
                idx = i - k
                if idx < 0 or np.isnan(np_ema[idx]):
                    long_setup_ok = False
                    break
                if not (np_close[idx] > np_open[idx] and np_close[idx] > np_ema[idx]):
                    long_setup_ok = False
                    break

            if long_setup_ok:
                first_idx = i - (nb_candles - 1)
                long_first_touch = np_low[first_idx] <= np_ema[first_idx]
                long_confirm_touch = (
                    setup_bar_can_retest
                    and np_low[i] <= np_ema[i] + tol_price
                )
                long_setup_ok = long_first_touch or long_confirm_touch
            else:
                long_first_touch = False
                long_confirm_touch = False

            # Short setup: N consecutive bearish candles closing below EMA
            short_setup_ok = True
            for k in range(nb_candles):
                idx = i - k
                if idx < 0 or np.isnan(np_ema[idx]):
                    short_setup_ok = False
                    break
                if not (np_close[idx] < np_open[idx] and np_close[idx] < np_ema[idx]):
                    short_setup_ok = False
                    break

            if short_setup_ok:
                first_idx = i - (nb_candles - 1)
                short_first_touch = np_high[first_idx] >= np_ema[first_idx]
                short_confirm_touch = (
                    setup_bar_can_retest
                    and np_high[i] >= np_ema[i] - tol_price
                )
                short_setup_ok = short_first_touch or short_confirm_touch
            else:
                short_first_touch = False
                short_confirm_touch = False

            # ============================================
            # BLOC 1: STATE MACHINE — SETUP / RETEST
            # ============================================
            if trade_state == 0:
                if long_setup_ok:
                    retest_already_done = long_confirm_touch
                    trade_state = 2 if retest_already_done else 1
                    setup_bar = i
                    ready_bar = i if retest_already_done else -1
                elif short_setup_ok:
                    retest_already_done = short_confirm_touch
                    trade_state = 6 if retest_already_done else 5
                    setup_bar = i
                    ready_bar = i if retest_already_done else -1

            elif trade_state == 1:  # SETUP LONG — waiting for retest
                if i - setup_bar >= max_bars:
                    trade_state = 0
                    ready_bar = -1
                elif np_low[i] <= np_ema[i] + tol_price:
                    if np_close[i] > np_ema[i]:
                        trade_state = 2
                        ready_bar = i
                    else:
                        trade_state = 0
                        ready_bar = -1

            elif trade_state == 2:  # READY LONG — waiting for breakout
                if i - setup_bar >= max_bars:
                    trade_state = 0
                    ready_bar = -1
                elif np_close[i] < np_ema[i]:
                    trade_state = 0
                    ready_bar = -1

            elif trade_state == 5:  # SETUP SHORT — waiting for retest
                if i - setup_bar >= max_bars:
                    trade_state = 0
                    ready_bar = -1
                elif np_high[i] >= np_ema[i] - tol_price:
                    if np_close[i] < np_ema[i]:
                        trade_state = 6
                        ready_bar = i
                    else:
                        trade_state = 0
                        ready_bar = -1

            elif trade_state == 6:  # READY SHORT — waiting for breakout
                if i - setup_bar >= max_bars:
                    trade_state = 0
                    ready_bar = -1
                elif np_close[i] > np_ema[i]:
                    trade_state = 0
                    ready_bar = -1

            # ============================================
            # BLOC 2: ENTRY CHECKS (from READY states)
            # ============================================
            # PineScript: canAct = bar_index > lastActionBar
            # We use: i > ready_bar (no entry on the readyBar itself)
            can_enter_long = (
                trade_state == 2
                and (ready_bar < 0 or i > ready_bar)
                and i > entry_bar  # not on same bar as previous entry
            )
            if can_enter_long:
                long_break_trigger = round_tick(np_high[i - 1] + tick_size)
                if np_high[i] >= long_break_trigger and np_close[i] >= np_ema[i]:
                    actual_entry = round_tick(np_close[i])
                    raw_sl = round_tick(np_low[i - 1] - sl_margin * tick_size)
                    raw_risk = actual_entry - raw_sl
                    actual_risk = min(raw_risk, max_stop_pts)
                    actual_sl = round_tick(actual_entry - actual_risk)

                    if actual_risk > 0:
                        entry_price = actual_entry
                        sl_price = actual_sl
                        tp1_price = get_tp1_long(actual_entry, actual_risk)
                        be_level = round_tick(actual_entry + actual_risk * rr_be)
                        entry_bar = i

                        long_entries[i] = True
                        sl_long_arr[i] = actual_sl
                        tp1_long_arr[i] = tp1_price
                        be_long_arr[i] = be_level

                        trade_state = 3  # LONG FULL (position active)

            can_enter_short = (
                trade_state == 6
                and (ready_bar < 0 or i > ready_bar)
                and i > entry_bar
            )
            if can_enter_short:
                short_break_trigger = round_tick(np_low[i - 1] - tick_size)
                if np_low[i] <= short_break_trigger and np_close[i] <= np_ema[i]:
                    actual_entry = round_tick(np_close[i])
                    raw_sl = round_tick(np_high[i - 1] + sl_margin * tick_size)
                    raw_risk = raw_sl - actual_entry
                    actual_risk = min(raw_risk, max_stop_pts)
                    actual_sl = round_tick(actual_entry + actual_risk)

                    if actual_risk > 0:
                        entry_price = actual_entry
                        sl_price = actual_sl
                        tp1_price = get_tp1_short(actual_entry, actual_risk)
                        be_level = round_tick(actual_entry - actual_risk * rr_be)
                        entry_bar = i

                        short_entries[i] = True
                        sl_short_arr[i] = actual_sl
                        tp1_short_arr[i] = tp1_price
                        be_short_arr[i] = be_level

                        trade_state = 7  # SHORT FULL (position active)

            # ============================================
            # BLOC 3: BAR-LEVEL POSITION MANAGEMENT
            # (mirrors PineScript for state tracking only —
            #  actual execution is handled by the simulator)
            # ============================================
            if i > entry_bar:
                # --- LONG FULL (state 3) ---
                if trade_state == 3:
                    if np_low[i] <= sl_price:
                        trade_state = 0
                    elif np_high[i] >= tp1_price:
                        sl_price = entry_price
                        trade_state = 4  # LONG PARTIAL
                    elif np_high[i] >= be_level:
                        sl_price = entry_price
                        trade_state = 9  # LONG BE

                # --- LONG BE (state 9) ---
                elif trade_state == 9:
                    if np_low[i] <= sl_price:
                        trade_state = 0
                    elif np_high[i] >= tp1_price:
                        trade_state = 4  # LONG PARTIAL

                # --- LONG PARTIAL (state 4) ---
                elif trade_state == 4:
                    if np_low[i] <= sl_price:
                        trade_state = 0
                    elif np_close[i] < np_ema[i]:
                        trade_state = 0

                # --- SHORT FULL (state 7) ---
                elif trade_state == 7:
                    if np_high[i] >= sl_price:
                        trade_state = 0
                    elif np_low[i] <= tp1_price:
                        sl_price = entry_price
                        trade_state = 8  # SHORT PARTIAL
                    elif np_low[i] <= be_level:
                        sl_price = entry_price
                        trade_state = 10  # SHORT BE

                # --- SHORT BE (state 10) ---
                elif trade_state == 10:
                    if np_high[i] >= sl_price:
                        trade_state = 0
                    elif np_low[i] <= tp1_price:
                        trade_state = 8  # SHORT PARTIAL

                # --- SHORT PARTIAL (state 8) ---
                elif trade_state == 8:
                    if np_high[i] >= sl_price:
                        trade_state = 0
                    elif np_close[i] > np_ema[i]:
                        trade_state = 0

            state_arr[i] = trade_state

        # --- Build output ---
        debug_frame = pd.DataFrame(
            {
                "Open": open_,
                "High": high,
                "Low": low,
                "Close": close,
                "ema": ema,
                "state": state_arr,
                "long_entry_signal": long_entries.astype(int),
                "short_entry_signal": short_entries.astype(int),
                "sl_long": sl_long_arr,
                "sl_short": sl_short_arr,
                "tp1_long": tp1_long_arr,
                "tp1_short": tp1_short_arr,
                "be_long": be_long_arr,
                "be_short": be_short_arr,
            },
            index=data.index,
        )

        return {
            "long_entries": pd.Series(long_entries, index=data.index),
            "short_entries": pd.Series(short_entries, index=data.index),
            "sl_long": pd.Series(sl_long_arr, index=data.index),
            "sl_short": pd.Series(sl_short_arr, index=data.index),
            "tp1_long": pd.Series(tp1_long_arr, index=data.index),
            "tp1_short": pd.Series(tp1_short_arr, index=data.index),
            "be_long": pd.Series(be_long_arr, index=data.index),
            "be_short": pd.Series(be_short_arr, index=data.index),
            "ema_main": ema,
            "ema_secondary": ema,  # same EMA, no TP2
            "cooldown_bars": 0,
            "debug_frame": debug_frame,
        }
