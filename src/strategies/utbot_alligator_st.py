"""
UTBot Alligator Supertrend strategy.

Translated from PineScript indicator UTBot-Alligator-ST.txt.
Combines UTBot trailing stop, Williams Alligator filter, and Supertrend
for trend direction + trailing SL.

Entry flow (state machine):
1. Supertrend changes direction → setup (WAIT_UTBOT)
2. UTBot signal fires + Alligator confirms + optional candle touch → compute
   retracement level (WAIT_RETRACE)
3. Price retraces to level within max_bars_retrace → ENTRY at retrace price

Exit flow (managed by simulator with Supertrend extensions):
- SL initially at Supertrend value ± buffer
- Trailing SL activates at rr_trailing × risk, follows Supertrend
- TP1 partial at bar close when RR level is touched
- TP2 partial at fixed RR price (touch)
- After TP2, remainder exits on trailing SL
- Supertrend reversal before trailing activation → immediate close at bar close
- Auto-close handled by simulator
"""

from .base import Strategy
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
from typing import Dict, Any

import warnings

warnings.filterwarnings("ignore", category=FutureWarning, module="pandas_ta_classic")


class UTBotAlligatorST(Strategy):
    """UTBot + Alligator + Supertrend — trend-following with retracement entry."""

    name = "UTBotAlligatorST"
    manual_exit = True
    use_simulator = True
    simulator_settings = {
        "tp1_execution_mode": "bar_close_if_touched",
    }

    default_params = {
        # UTBot
        "ut_key": 1.0,
        "ut_atr_period": 10,
        "use_heikin_ashi": False,
        # Supertrend
        "st_atr_period": 10,
        "st_multiplier": 3.0,
        # Alligator
        "jaw_length": 13,
        "teeth_length": 8,
        "lips_length": 5,
        "jaw_offset": 8,
        "teeth_offset": 5,
        "lips_offset": 3,
        "alligator_mode": "Bougie courante",  # "Bougie courante", "Offset", "Les deux"
        "require_touch_alligator": True,
        # Position
        "sl_buffer_ticks": 0,
        "max_stop_points": 60.0,
        "rr_tp1": 2.0,
        "tp1_points": 50.0,
        "rr_tp2": 3.0,
        "rr_trailing": 1.0,
        "retrace_pct": 50.0,
        "max_bars_retrace": 2,
        # Partial TPs
        "tp1_partial_pct": 0.25,
        "tp2_partial_pct": 0.25,
        # Injected by engine
        "tick_size": 0.25,
    }

    param_ranges = {
        "ut_key": [0.5, 1.0, 1.5, 2.0],
        "ut_atr_period": [7, 10, 14],
        "st_atr_period": [7, 10, 14],
        "st_multiplier": [2.0, 2.5, 3.0, 3.5],
        "jaw_length": [10, 13, 15],
        "rr_tp1": [1.5, 2.0, 2.5, 3.0],
        "tp1_points": [30.0, 40.0, 50.0, 60.0],
        "rr_tp2": [2.5, 3.0, 3.5, 4.0],
        "rr_trailing": [0.5, 1.0, 1.5],
        "retrace_pct": [40.0, 50.0, 60.0],
        "max_bars_retrace": [1, 2, 3],
        "max_stop_points": [40.0, 50.0, 60.0, 80.0],
        "sl_buffer_ticks": [0, 1, 2, 3],
    }

    def get_simulator_settings(self, params=None):
        p = self.get_params(params)
        settings = self.simulator_settings.copy()
        settings["tp1_partial_pct"] = p.get("tp1_partial_pct", 0.25)
        settings["tp2_partial_pct"] = p.get("tp2_partial_pct", 0.25)
        return settings

    # ------------------------------------------------------------------
    # SMMA (= RMA / Wilder's smoothing) — matches PineScript exactly
    # ------------------------------------------------------------------

    @staticmethod
    def _smma(values: np.ndarray, length: int) -> np.ndarray:
        """
        Compute SMMA matching PineScript's recursive definition.
        s := na(s[1]) ? sma(src, length) : (s[1] * (length - 1) + src) / length
        """
        n = len(values)
        result = np.full(n, np.nan)
        if n < length:
            return result
        # Seed with SMA
        result[length - 1] = np.mean(values[:length])
        for i in range(length, n):
            result[i] = (result[i - 1] * (length - 1) + values[i]) / length
        return result

    # ------------------------------------------------------------------
    # UTBot Trailing Stop — matches PineScript exactly
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_utbot(src: np.ndarray, atr: np.ndarray, key_value: float):
        """Compute UTBot trailing stop and buy/sell signals."""
        n = len(src)
        nLoss = key_value * atr
        trail = np.zeros(n)

        for i in range(1, n):
            prev_trail = trail[i - 1]
            curr_src = src[i]
            prev_src = src[i - 1]
            curr_nLoss = nLoss[i] if not np.isnan(nLoss[i]) else 0.0

            if curr_src > prev_trail and prev_src > prev_trail:
                trail[i] = max(prev_trail, curr_src - curr_nLoss)
            elif curr_src < prev_trail and prev_src < prev_trail:
                trail[i] = min(prev_trail, curr_src + curr_nLoss)
            elif curr_src > prev_trail:
                trail[i] = curr_src - curr_nLoss
            else:
                trail[i] = curr_src + curr_nLoss

        # UTBot signals: crossover/crossunder of src and trail
        # utEma = ta.ema(utSrc, 1) is just src itself
        # utAbove = crossover(src, trail): prev_src <= prev_trail and curr_src > trail
        # utBotBuy = src > trail and utAbove
        ut_buy = np.zeros(n, dtype=bool)
        ut_sell = np.zeros(n, dtype=bool)

        for i in range(1, n):
            cross_over = src[i - 1] <= trail[i - 1] and src[i] > trail[i]
            cross_under = src[i - 1] >= trail[i - 1] and src[i] < trail[i]
            ut_buy[i] = src[i] > trail[i] and cross_over
            ut_sell[i] = src[i] < trail[i] and cross_under

        return trail, ut_buy, ut_sell

    # ------------------------------------------------------------------
    # Supertrend — matches PineScript exactly
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_supertrend(
        close: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        atr: np.ndarray,
        multiplier: float,
    ):
        """Compute Supertrend matching PineScript v6."""
        n = len(close)
        hl2 = (high + low) / 2.0

        st_up = np.full(n, np.nan)
        st_dn = np.full(n, np.nan)
        trend = np.ones(n, dtype=int)
        st_value = np.full(n, np.nan)

        # First bar init
        if n > 0 and not np.isnan(atr[0]):
            st_up[0] = hl2[0] - multiplier * atr[0]
            st_dn[0] = hl2[0] + multiplier * atr[0]
            st_value[0] = st_up[0]

        for i in range(1, n):
            if np.isnan(atr[i]):
                st_up[i] = st_up[i - 1] if not np.isnan(st_up[i - 1]) else hl2[i]
                st_dn[i] = st_dn[i - 1] if not np.isnan(st_dn[i - 1]) else hl2[i]
                trend[i] = trend[i - 1]
                st_value[i] = st_up[i] if trend[i] == 1 else st_dn[i]
                continue

            up = hl2[i] - multiplier * atr[i]
            dn = hl2[i] + multiplier * atr[i]

            # Up band ratchets up
            prev_up = st_up[i - 1] if not np.isnan(st_up[i - 1]) else up
            st_up[i] = max(up, prev_up) if close[i - 1] > prev_up else up

            # Down band ratchets down
            prev_dn = st_dn[i - 1] if not np.isnan(st_dn[i - 1]) else dn
            st_dn[i] = min(dn, prev_dn) if close[i - 1] < prev_dn else dn

            # Trend direction
            prev_trend = trend[i - 1]
            prev_dn_chk = st_dn[i - 1] if not np.isnan(st_dn[i - 1]) else dn
            prev_up_chk = st_up[i - 1] if not np.isnan(st_up[i - 1]) else up

            if prev_trend == -1 and close[i] > prev_dn_chk:
                trend[i] = 1
            elif prev_trend == 1 and close[i] < prev_up_chk:
                trend[i] = -1
            else:
                trend[i] = prev_trend

            st_value[i] = st_up[i] if trend[i] == 1 else st_dn[i]

        # Trend change signals
        st_buy_signal = np.zeros(n, dtype=bool)
        st_sell_signal = np.zeros(n, dtype=bool)
        for i in range(1, n):
            st_buy_signal[i] = trend[i] == 1 and trend[i - 1] == -1
            st_sell_signal[i] = trend[i] == -1 and trend[i - 1] == 1

        return st_up, st_dn, trend, st_value, st_buy_signal, st_sell_signal

    # ------------------------------------------------------------------
    # Main signal generation
    # ------------------------------------------------------------------

    def generate_signals(
        self, data: pd.DataFrame, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        p = self.get_params(params)

        close = data["Close"].values
        open_ = data["Open"].values
        high = data["High"].values
        low = data["Low"].values
        hl2 = (high + low) / 2.0
        n = len(data)

        tick_size = p["tick_size"]

        def round_tick(price):
            if tick_size > 0:
                return round(price / tick_size) * tick_size
            return price

        # ----------------------------------------------------------------
        # 1. Alligator (SMMA on hl2)
        # ----------------------------------------------------------------
        jaw_raw = self._smma(hl2, p["jaw_length"])
        teeth_raw = self._smma(hl2, p["teeth_length"])
        lips_raw = self._smma(hl2, p["lips_length"])

        jaw_off = p["jaw_offset"]
        teeth_off = p["teeth_offset"]
        lips_off = p["lips_offset"]

        # "On chart bar" = value plotted with offset, so we look BACK
        jaw_on_chart = np.full(n, np.nan)
        teeth_on_chart = np.full(n, np.nan)
        lips_on_chart = np.full(n, np.nan)
        for i in range(jaw_off, n):
            jaw_on_chart[i] = jaw_raw[i - jaw_off]
        for i in range(teeth_off, n):
            teeth_on_chart[i] = teeth_raw[i - teeth_off]
        for i in range(lips_off, n):
            lips_on_chart[i] = lips_raw[i - lips_off]

        # Chart-bar conditions: lips > teeth > jaw
        alli_chart_bull = np.zeros(n, dtype=bool)
        alli_chart_bear = np.zeros(n, dtype=bool)
        for i in range(n):
            j, t, li = jaw_on_chart[i], teeth_on_chart[i], lips_on_chart[i]
            if not (np.isnan(j) or np.isnan(t) or np.isnan(li)):
                alli_chart_bull[i] = li > t and t > j
                alli_chart_bear[i] = li < t and t < j

        # Offset conditions: current raw values (no lookback)
        alli_off_bull = np.zeros(n, dtype=bool)
        alli_off_bear = np.zeros(n, dtype=bool)
        for i in range(n):
            j, t, li = jaw_raw[i], teeth_raw[i], lips_raw[i]
            if not (np.isnan(j) or np.isnan(t) or np.isnan(li)):
                alli_off_bull[i] = li > t and t > j
                alli_off_bear[i] = li < t and t < j

        mode = p["alligator_mode"]
        if mode == "Bougie courante":
            alli_bull = alli_chart_bull
            alli_bear = alli_chart_bear
        elif mode == "Offset":
            alli_bull = alli_off_bull
            alli_bear = alli_off_bear
        else:  # "Les deux"
            alli_bull = alli_chart_bull & alli_off_bull
            alli_bear = alli_chart_bear & alli_off_bear

        # Candle touches Alligator line (on chart bar values)
        require_touch = p["require_touch_alligator"]
        touches_alli = np.ones(n, dtype=bool)
        if require_touch:
            for i in range(n):
                touch = False
                for level in [jaw_on_chart[i], teeth_on_chart[i], lips_on_chart[i]]:
                    if not np.isnan(level) and low[i] <= level and high[i] >= level:
                        touch = True
                        break
                touches_alli[i] = touch

        # ----------------------------------------------------------------
        # 2. UTBot trailing stop
        # ----------------------------------------------------------------
        if p["use_heikin_ashi"]:
            ha_close = (open_ + high + low + close) / 4.0
            ha_open = np.zeros(n)
            ha_open[0] = open_[0]
            for i in range(1, n):
                ha_open[i] = (ha_open[i - 1] + ha_close[i - 1]) / 2.0
            ut_src = ha_close
        else:
            ut_src = close.copy()

        # ATR always on real prices
        atr_ut = ta.atr(
            pd.Series(high), pd.Series(low), pd.Series(close),
            length=p["ut_atr_period"],
        ).values

        ut_trail, ut_buy, ut_sell = self._compute_utbot(
            ut_src, atr_ut, p["ut_key"]
        )

        # ----------------------------------------------------------------
        # 3. Supertrend
        # ----------------------------------------------------------------
        atr_st = ta.atr(
            pd.Series(high), pd.Series(low), pd.Series(close),
            length=p["st_atr_period"],
        ).values

        st_up, st_dn, st_trend, st_value, st_buy_signal, st_sell_signal = (
            self._compute_supertrend(close, high, low, atr_st, p["st_multiplier"])
        )

        # ----------------------------------------------------------------
        # 4. State machine for entry detection + simplified position tracking
        # ----------------------------------------------------------------
        # States 0-4: entry detection.  States 5-12: position open.
        # The position tracking is simplified (no PnL, just SL/TP state)
        # so that the state machine correctly pauses entry detection during
        # open positions.  The real simulator handles execution and sizing.

        long_entries = np.zeros(n, dtype=bool)
        short_entries = np.zeros(n, dtype=bool)
        sl_long_arr = np.full(n, np.nan)
        sl_short_arr = np.full(n, np.nan)
        tp1_long_arr = np.full(n, np.nan)
        tp1_short_arr = np.full(n, np.nan)
        entry_price_long_arr = np.full(n, np.nan)
        entry_price_short_arr = np.full(n, np.nan)
        tp2_long_arr = np.full(n, np.nan)
        tp2_short_arr = np.full(n, np.nan)

        # State machine vars
        trade_state = 0
        retrace_level = np.nan
        signal_bar = -1
        entry_price = np.nan
        sl_price = np.nan
        tp1_price = np.nan
        tp2_price = np.nan
        initial_risk = np.nan
        current_side = 0  # 1=long, -1=short
        entry_bar = -1
        last_action_bar = -1
        trailing_active = False
        tp1_hit = False
        tp2_hit = False

        sl_buffer = p["sl_buffer_ticks"] * tick_size
        max_stop = p["max_stop_points"]
        rr_tp1 = p["rr_tp1"]
        tp1_pts = p["tp1_points"]
        rr_tp2 = p["rr_tp2"]
        rr_trail = p["rr_trailing"]
        retrace_pct = p["retrace_pct"]
        max_bars = p["max_bars_retrace"]

        start_bar = max(
            p["jaw_length"] + p["jaw_offset"],
            p["ut_atr_period"],
            p["st_atr_period"],
        ) + 5

        # Debug arrays for state tracking
        trade_state_arr = np.zeros(n, dtype=int)

        for i in range(start_bar, n):
            is_entry_bar = i == entry_bar

            # ========================================================
            # BLOC 1: INVALIDATION + SETUP DETECTION
            # ========================================================

            # Invalidation of waiting states if Supertrend changes
            if trade_state == 1 and st_trend[i] != 1:
                trade_state = 0
            elif trade_state == 2 and st_trend[i] != -1:
                trade_state = 0
            elif trade_state == 3:
                if st_trend[i] != 1:
                    trade_state = 0
                elif i - signal_bar > max_bars:
                    trade_state = 1  # back to waiting UTBot
            elif trade_state == 4:
                if st_trend[i] != -1:
                    trade_state = 0
                elif i - signal_bar > max_bars:
                    trade_state = 2  # back to waiting UTBot

            # Setup detection (when FLAT)
            if trade_state == 0:
                if st_buy_signal[i]:
                    trade_state = 1
                elif st_sell_signal[i]:
                    trade_state = 2
                elif st_trend[i] == 1:
                    trade_state = 1
                elif st_trend[i] == -1:
                    trade_state = 2

            # ========================================================
            # BLOC 2: WAIT UTBOT + ALLIGATOR
            # ========================================================

            if trade_state == 1:
                if ut_buy[i] and alli_bull[i] and touches_alli[i]:
                    retrace_level = round_tick(
                        low[i] + (high[i] - low[i]) * (retrace_pct / 100.0)
                    )
                    signal_bar = i
                    trade_state = 3

            elif trade_state == 2:
                if ut_sell[i] and alli_bear[i] and touches_alli[i]:
                    retrace_level = round_tick(
                        high[i] - (high[i] - low[i]) * (retrace_pct / 100.0)
                    )
                    signal_bar = i
                    trade_state = 4

            # ========================================================
            # BLOC 3: WAIT RETRACE
            # ========================================================

            elif trade_state == 3:
                # Long retrace: price must come down to touch retrace_level
                if low[i] <= retrace_level and i > last_action_bar:
                    calc_entry = round_tick(retrace_level)
                    raw_sl = round_tick(st_value[i] - sl_buffer)
                    raw_risk = calc_entry - raw_sl
                    actual_risk = min(raw_risk, max_stop)
                    actual_sl = round_tick(calc_entry - actual_risk)

                    if actual_risk > 0:
                        rr_target = calc_entry + actual_risk * rr_tp1
                        fixed_target = calc_entry + tp1_pts if tp1_pts > 0 else rr_target
                        calc_tp1 = round_tick(
                            min(rr_target, fixed_target) if tp1_pts > 0 else rr_target
                        )
                        calc_tp2 = round_tick(calc_entry + actual_risk * rr_tp2)

                        long_entries[i] = True
                        entry_price_long_arr[i] = calc_entry
                        sl_long_arr[i] = actual_sl
                        tp1_long_arr[i] = calc_tp1
                        tp2_long_arr[i] = calc_tp2

                        # Enter simplified position tracking
                        entry_price = calc_entry
                        sl_price = actual_sl
                        tp1_price = calc_tp1
                        tp2_price = calc_tp2
                        initial_risk = actual_risk
                        entry_bar = i
                        last_action_bar = i
                        current_side = 1
                        trailing_active = False
                        tp1_hit = False
                        tp2_hit = False
                        trade_state = 5
                    else:
                        trade_state = 0

            elif trade_state == 4:
                # Short retrace: price must come up to touch retrace_level
                if high[i] >= retrace_level and i > last_action_bar:
                    calc_entry = round_tick(retrace_level)
                    raw_sl = round_tick(st_value[i] + sl_buffer)
                    raw_risk = raw_sl - calc_entry
                    actual_risk = min(raw_risk, max_stop)
                    actual_sl = round_tick(calc_entry + actual_risk)

                    if actual_risk > 0:
                        rr_target = calc_entry - actual_risk * rr_tp1
                        fixed_target = calc_entry - tp1_pts if tp1_pts > 0 else rr_target
                        calc_tp1 = round_tick(
                            max(rr_target, fixed_target) if tp1_pts > 0 else rr_target
                        )
                        calc_tp2 = round_tick(calc_entry - actual_risk * rr_tp2)

                        short_entries[i] = True
                        entry_price_short_arr[i] = calc_entry
                        sl_short_arr[i] = actual_sl
                        tp1_short_arr[i] = calc_tp1
                        tp2_short_arr[i] = calc_tp2

                        entry_price = calc_entry
                        sl_price = actual_sl
                        tp1_price = calc_tp1
                        tp2_price = calc_tp2
                        initial_risk = actual_risk
                        entry_bar = i
                        last_action_bar = i
                        current_side = -1
                        trailing_active = False
                        tp1_hit = False
                        tp2_hit = False
                        trade_state = 8
                    else:
                        trade_state = 0

            # ========================================================
            # BLOC 4: SIMPLIFIED POSITION MANAGEMENT
            # (mirrors PineScript states 5-12 for correct entry detection)
            # ========================================================

            elif trade_state >= 5 and not is_entry_bar:
                closed = False

                if current_side == 1:
                    # --- LONG position management ---

                    # Update trailing SL in trailing states (only when trend is bullish)
                    if trade_state in (6, 7, 11) and st_trend[i] == 1:
                        new_sl = round_tick(st_value[i] - sl_buffer)
                        if trade_state in (7, 11):
                            sl_price = max(sl_price, max(new_sl, entry_price))
                        else:
                            if new_sl > sl_price:
                                sl_price = new_sl

                    # Check SL
                    if low[i] <= sl_price:
                        closed = True

                    # Supertrend reversal (FULL state only)
                    elif trade_state == 5 and st_trend[i] != 1:
                        closed = True

                    else:
                        # Trailing activation
                        trail_level = entry_price + initial_risk * rr_trail
                        if high[i] >= trail_level and trade_state == 5:
                            trailing_active = True
                            if st_trend[i] == 1:
                                sl_price = round_tick(st_value[i] - sl_buffer)
                            trade_state = 6

                        # TP1 check
                        if not tp1_hit and high[i] >= tp1_price:
                            tp1_hit = True
                            sl_price = max(sl_price, entry_price)
                            if trade_state in (5, 6):
                                trade_state = 7
                            # Same-bar TP2 check
                            if not tp2_hit and high[i] >= tp2_price:
                                tp2_hit = True
                                trade_state = 11

                        # TP2 check (after TP1, different bar)
                        elif tp1_hit and not tp2_hit and high[i] >= tp2_price:
                            tp2_hit = True
                            trade_state = 11

                        # Trailing activation in TP1/TP2 states
                        if trade_state in (7, 11) and high[i] >= trail_level:
                            trailing_active = True

                elif current_side == -1:
                    # --- SHORT position management ---

                    # Update trailing SL (only when trend is bearish)
                    if trade_state in (9, 10, 12) and st_trend[i] == -1:
                        new_sl = round_tick(st_value[i] + sl_buffer)
                        if trade_state in (10, 12):
                            sl_price = min(sl_price, min(new_sl, entry_price))
                        else:
                            if new_sl < sl_price:
                                sl_price = new_sl

                    # Check SL
                    if high[i] >= sl_price:
                        closed = True

                    # Supertrend reversal (FULL state only)
                    elif trade_state == 8 and st_trend[i] != -1:
                        closed = True

                    else:
                        # Trailing activation
                        trail_level = entry_price - initial_risk * rr_trail
                        if low[i] <= trail_level and trade_state == 8:
                            trailing_active = True
                            if st_trend[i] == -1:
                                sl_price = round_tick(st_value[i] + sl_buffer)
                            trade_state = 9

                        # TP1 check
                        if not tp1_hit and low[i] <= tp1_price:
                            tp1_hit = True
                            sl_price = min(sl_price, entry_price)
                            if trade_state in (8, 9):
                                trade_state = 10
                            # Same-bar TP2
                            if not tp2_hit and low[i] <= tp2_price:
                                tp2_hit = True
                                trade_state = 12

                        # TP2 (different bar)
                        elif tp1_hit and not tp2_hit and low[i] <= tp2_price:
                            tp2_hit = True
                            trade_state = 12

                        # Trailing activation in TP1/TP2 states
                        if trade_state in (10, 12) and low[i] <= trail_level:
                            trailing_active = True

                if closed:
                    current_side = 0
                    trailing_active = False
                    last_action_bar = i
                    trade_state = 0

            trade_state_arr[i] = trade_state

        # ----------------------------------------------------------------
        # 5. Build output
        # ----------------------------------------------------------------
        nan_series = pd.Series(np.full(n, np.nan), index=data.index)

        debug_frame = pd.DataFrame(
            {
                "Open": open_,
                "High": high,
                "Low": low,
                "Close": close,
                "jaw": jaw_raw,
                "teeth": teeth_raw,
                "lips": lips_raw,
                "jaw_on_chart": jaw_on_chart,
                "teeth_on_chart": teeth_on_chart,
                "lips_on_chart": lips_on_chart,
                "alli_chart_bull": alli_chart_bull.astype(int),
                "alli_chart_bear": alli_chart_bear.astype(int),
                "alli_off_bull": alli_off_bull.astype(int),
                "alli_off_bear": alli_off_bear.astype(int),
                "touches_alli": touches_alli.astype(int),
                "ut_trail": ut_trail,
                "ut_buy": ut_buy.astype(int),
                "ut_sell": ut_sell.astype(int),
                "st_trend": st_trend,
                "st_value": st_value,
                "st_up": st_up,
                "st_dn": st_dn,
                "st_buy_signal": st_buy_signal.astype(int),
                "st_sell_signal": st_sell_signal.astype(int),
                "trade_state": trade_state_arr,
                "long_entry_signal": long_entries.astype(int),
                "short_entry_signal": short_entries.astype(int),
                "entry_price_long": entry_price_long_arr,
                "entry_price_short": entry_price_short_arr,
                "sl_long": sl_long_arr,
                "sl_short": sl_short_arr,
                "tp1_long": tp1_long_arr,
                "tp1_short": tp1_short_arr,
                "tp2_long": tp2_long_arr,
                "tp2_short": tp2_short_arr,
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
            "entry_price_long": pd.Series(entry_price_long_arr, index=data.index),
            "entry_price_short": pd.Series(entry_price_short_arr, index=data.index),
            "tp2_long": pd.Series(tp2_long_arr, index=data.index),
            "tp2_short": pd.Series(tp2_short_arr, index=data.index),
            "supertrend": pd.Series(st_value, index=data.index),
            "supertrend_trend": pd.Series(st_trend, index=data.index),
            "ema_main": nan_series,
            "ema_secondary": nan_series,
            "rr_trailing": rr_trail,
            "sl_buffer": sl_buffer,
            "cooldown_bars": 0,
            "debug_frame": debug_frame,
        }
