from .base import Strategy
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
from typing import Tuple, Dict, Any

class UTBotSTC(Strategy):
    """
    UTBot Strategy with STC Filter and Heikin Ashi option.
    Based on Pine Script: 'UTBot-STC Strategy'.

    Key differences from UTBotHeikin:
    - Uses STC oscillator as filter instead of RSI/EMA200/Ribbon
    - Fixed SL/TP levels (not trailing after partial)
    - SL based on signal candle high/low + ticks offset
    - TP based on risk/reward ratio

    IMPORTANT: In Pine Script, when useHeikinAshi=True:
    - ATR is calculated on REAL prices (ta.atr uses chart's H/L/C)
    - STC is calculated on REAL close prices
    - Only 'src' for trailing stop uses HA close via request.security()
    """

    name = "UTBotSTC"
    manual_exit = True

    default_params = {
        # UTBot Settings
        "key_value": 1.0,
        "atr_period": 10,
        "use_heikin_ashi": False,

        # STC Settings
        "stc_length": 12,
        "stc_fast_length": 26,
        "stc_slow_length": 50,

        # STC Level Filters
        "stc_min_long": 1.0,
        "stc_max_long": 75.0,
        "stc_min_short": 25.0,
        "stc_max_short": 99.0,

        # Position Management
        "stop_ticks": 3,
        "risk_reward": 2.0,
        "tick_size": 0.25
    }

    def generate_signals(
        self,
        data: pd.DataFrame,
        params: Dict[str, Any] = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
        p = self.get_params(params)

        # Ensure we have enough data
        min_len = max(p['stc_slow_length'], p['atr_period']) + p['stc_length'] + 10
        if len(data) < min_len:
            empty = pd.Series(False, index=data.index)
            zeros = pd.Series(0.0, index=data.index)
            nans = pd.Series(np.nan, index=data.index)
            return empty, empty, empty, empty, zeros, nans, nans

        # REAL prices - always used for ATR, STC, and execution
        real_close = data['Close']
        real_open = data['Open']
        real_high = data['High']
        real_low = data['Low']

        # ===========================================
        # 1. Heikin Ashi Calculation
        # ===========================================
        # When useHeikinAshi=True AND chart is displayed as HA on TradingView:
        # - ALL indicators (ATR, STC) use HA prices from the chart
        # - src also uses HA close
        # This matches TradingView behavior when viewing HA chart

        if p['use_heikin_ashi']:
            ha_close = (real_open + real_high + real_low + real_close) / 4

            # HA Open requires iteration
            np_ha_open = np.zeros(len(data))
            np_ha_open[0] = real_open.values[0]
            np_ha_close = ha_close.values

            for i in range(1, len(data)):
                np_ha_open[i] = (np_ha_open[i-1] + np_ha_close[i-1]) / 2

            ha_open = pd.Series(np_ha_open, index=data.index)

            # HA High/Low (max/min of real H/L and HA O/C)
            ha_high = pd.DataFrame({'a': real_high, 'b': ha_open, 'c': ha_close}).max(axis=1)
            ha_low = pd.DataFrame({'a': real_low, 'b': ha_open, 'c': ha_close}).min(axis=1)

            # Use HA prices for everything when in HA mode
            calc_close = ha_close
            calc_high = ha_high
            calc_low = ha_low
            src = ha_close
        else:
            calc_close = real_close
            calc_high = real_high
            calc_low = real_low
            src = real_close

        # ===========================================
        # 2. UTBot Trailing Stop Calculation
        # ===========================================
        # ATR uses calc prices (HA when enabled, real otherwise)
        xATR = ta.atr(calc_high, calc_low, calc_close, length=p['atr_period'])
        nLoss = p['key_value'] * xATR

        np_src = src.values
        np_nLoss = nLoss.values
        np_trail = np.zeros(len(data))

        # Pine initialization: var float xATRTrailingStop = na
        # On first valid bar, it becomes src - nLoss or src + nLoss
        np_trail[0] = 0.0  # Pine uses nz(..., 0)

        for i in range(1, len(data)):
            prev_trail = np_trail[i-1]
            curr_src = np_src[i]
            prev_src = np_src[i-1]
            curr_nLoss = np_nLoss[i] if not np.isnan(np_nLoss[i]) else 0

            # Pine logic:
            # xATRTrailingStop := src > nz(xATRTrailingStop[1], 0) and src[1] > nz(xATRTrailingStop[1], 0) ?
            #    math.max(nz(xATRTrailingStop[1]), src - nLoss) :
            #    src < nz(xATRTrailingStop[1], 0) and src[1] < nz(xATRTrailingStop[1], 0) ?
            #    math.min(nz(xATRTrailingStop[1]), src + nLoss) :
            #    src > nz(xATRTrailingStop[1], 0) ? src - nLoss : src + nLoss

            if (curr_src > prev_trail) and (prev_src > prev_trail):
                np_trail[i] = max(prev_trail, curr_src - curr_nLoss)
            elif (curr_src < prev_trail) and (prev_src < prev_trail):
                np_trail[i] = min(prev_trail, curr_src + curr_nLoss)
            elif curr_src > prev_trail:
                np_trail[i] = curr_src - curr_nLoss
            else:
                np_trail[i] = curr_src + curr_nLoss

        xATRTrailingStop = pd.Series(np_trail, index=data.index)

        # ===========================================
        # 3. UTBot Signal Generation
        # ===========================================
        # Pine:
        # ema = ta.ema(src, 1)  -> effectively just src
        # above = ta.crossover(ema, xATRTrailingStop)
        # below = ta.crossover(xATRTrailingStop, ema)
        # utBotLong = src > xATRTrailingStop and above
        # utBotShort = src < xATRTrailingStop and below

        prev_src = src.shift(1)
        prev_trail = xATRTrailingStop.shift(1)

        # Crossover detection
        above = (src > xATRTrailingStop) & (prev_src <= prev_trail)
        below = (src < xATRTrailingStop) & (prev_src >= prev_trail)

        utbot_long = (src > xATRTrailingStop) & above
        utbot_short = (src < xATRTrailingStop) & below

        # ===========================================
        # 4. STC Calculation (uses chart prices - HA when enabled)
        # ===========================================
        # Pine: macdVal = calcMACD(close, fastLen, slowLen)
        # When TradingView displays HA chart, 'close' is the HA close

        stc_len = p['stc_length']
        fast_len = p['stc_fast_length']
        slow_len = p['stc_slow_length']

        # MACD on calc_close (HA when enabled, real otherwise)
        fast_ma = ta.ema(calc_close, length=fast_len)
        slow_ma = ta.ema(calc_close, length=slow_len)
        macd_val = fast_ma - slow_ma

        # Convert to numpy for loop
        np_macd = macd_val.fillna(0).values

        # Rolling min/max for MACD
        macd_s = pd.Series(np_macd)
        low_macd = macd_s.rolling(window=stc_len, min_periods=stc_len).min().bfill().values
        high_macd = macd_s.rolling(window=stc_len, min_periods=stc_len).max().bfill().values

        # Step 1: %K of MACD -> smoothed to PF
        pf_series = np.zeros(len(data))
        pff_prev = 0.0
        pf_prev = 0.0
        factor = 0.5

        for i in range(len(data)):
            m_val = np_macd[i]
            l_val = low_macd[i]
            h_val = high_macd[i]
            rng1 = h_val - l_val

            # pff := range1 > 0 ? (macdVal - lowest) / range1 * 100 : nz(pff[1])
            if rng1 > 0:
                pff = (m_val - l_val) / rng1 * 100
            else:
                pff = pff_prev

            pff_prev = pff

            # pf := na(pf[1]) ? pff : pf[1] + factor * (pff - pf[1])
            # First iteration: pf_prev is 0, so pf = 0 + 0.5 * (pff - 0) = 0.5 * pff
            pf = pf_prev + factor * (pff - pf_prev)
            pf_prev = pf
            pf_series[i] = pf

        # Step 2: %K of PF -> smoothed to PFF2 (final STC)
        pf_s = pd.Series(pf_series)
        low_pf = pf_s.rolling(window=stc_len, min_periods=stc_len).min().bfill().values
        high_pf = pf_s.rolling(window=stc_len, min_periods=stc_len).max().bfill().values

        stc_final = np.zeros(len(data))
        pfff_prev = 0.0
        pff2_prev = 0.0

        for i in range(len(data)):
            val = pf_series[i]
            l_val = low_pf[i]
            h_val = high_pf[i]
            rng2 = h_val - l_val

            # pfff := range2 > 0 ? (pf - lowest2) / range2 * 100 : nz(pfff[1])
            if rng2 > 0:
                pfff = (val - l_val) / rng2 * 100
            else:
                pfff = pfff_prev

            pfff_prev = pfff

            # pff2 := na(pff2[1]) ? pfff : pff2[1] + factor * (pfff - pff2[1])
            pff2 = pff2_prev + factor * (pfff - pff2_prev)
            pff2_prev = pff2
            stc_final[i] = pff2

        stc_val = pd.Series(stc_final, index=data.index)

        # ===========================================
        # 5. STC Filter Conditions
        # ===========================================
        stc_prev = stc_val.shift(1)

        stc_rising = stc_val > stc_prev
        stc_falling = stc_val < stc_prev

        stc_valid_long = (stc_val >= p['stc_min_long']) & (stc_val <= p['stc_max_long']) & stc_rising
        stc_valid_short = (stc_val >= p['stc_min_short']) & (stc_val <= p['stc_max_short']) & stc_falling

        # ===========================================
        # 6. Combined Entry Signals
        # ===========================================
        long_signal = utbot_long & stc_valid_long
        short_signal = utbot_short & stc_valid_short

        # ===========================================
        # 7. Position Management (Fixed SL/TP)
        # ===========================================
        long_entries = pd.Series(False, index=data.index)
        long_exits = pd.Series(False, index=data.index)
        short_entries = pd.Series(False, index=data.index)
        short_exits = pd.Series(False, index=data.index)

        # Initialize exec_prices with REAL Close
        exec_prices = real_close.copy()
        sl_dists = pd.Series(np.nan, index=data.index)
        exit_ratios = pd.Series(1.0, index=data.index)

        # Helper for rounding
        tick_sz = p['tick_size'] if p['tick_size'] > 0 else 0.25
        def round_to_tick(price):
            return round(price / tick_sz) * tick_sz

        # Loop variables
        in_pos = False
        pos_side = 0  # 1 = Long, -1 = Short
        entry_price = 0.0
        stop_price = 0.0
        tp_price = 0.0
        entry_idx = -1  # Track entry bar index for exit protection
        stop_ticks = p['stop_ticks']
        rr = p['risk_reward']

        np_long_sig = long_signal.values
        np_short_sig = short_signal.values

        # Pre-convert to numpy for speed
        # Use calc prices (HA when enabled) to match TradingView chart behavior
        np_calc_close = calc_close.values
        np_calc_high = calc_high.values
        np_calc_low = calc_low.values

        for i in range(1, len(data)):

            # ===========================================
            # Check Exits FIRST (but NOT on entry bar)
            # ===========================================
            # Pine: if inPosition and bar_index > signalBar
            # Use calc (chart) prices to detect SL/TP hits
            if in_pos and i > entry_idx:
                curr_low = np_calc_low[i]
                curr_high = np_calc_high[i]

                if pos_side == 1:  # Long position
                    # Check SL first (priority over TP in same bar)
                    if curr_low <= stop_price:
                        long_exits.iloc[i] = True
                        exec_prices.iloc[i] = stop_price
                        in_pos = False
                        pos_side = 0
                        entry_idx = -1
                    elif curr_high >= tp_price:
                        long_exits.iloc[i] = True
                        exec_prices.iloc[i] = tp_price
                        in_pos = False
                        pos_side = 0
                        entry_idx = -1

                elif pos_side == -1:  # Short position
                    # Check SL first
                    if curr_high >= stop_price:
                        short_exits.iloc[i] = True
                        exec_prices.iloc[i] = stop_price
                        in_pos = False
                        pos_side = 0
                        entry_idx = -1
                    elif curr_low <= tp_price:
                        short_exits.iloc[i] = True
                        exec_prices.iloc[i] = tp_price
                        in_pos = False
                        pos_side = 0
                        entry_idx = -1

            # ===========================================
            # Check Entries (only if not in position)
            # ===========================================
            if not in_pos:
                if np_long_sig[i]:
                    # Entry at close of signal bar (chart close - HA when enabled)
                    entry_p = round_to_tick(np_calc_close[i])

                    # SL/TP based on SIGNAL CANDLE's chart low (HA when enabled)
                    sig_low = np_calc_low[i]
                    stop_p = round_to_tick(sig_low - stop_ticks * tick_sz)
                    risk_amt = entry_p - stop_p
                    tp_p = round_to_tick(entry_p + risk_amt * rr)

                    if risk_amt > 0:
                        long_entries.iloc[i] = True
                        exec_prices.iloc[i] = entry_p
                        in_pos = True
                        pos_side = 1
                        entry_idx = i  # Store entry bar index
                        entry_price = entry_p
                        stop_price = stop_p
                        tp_price = tp_p
                        sl_dists.iloc[i] = risk_amt

                elif np_short_sig[i]:
                    # Entry at close of signal bar (chart close - HA when enabled)
                    entry_p = round_to_tick(np_calc_close[i])

                    # SL/TP based on SIGNAL CANDLE's chart high (HA when enabled)
                    sig_high = np_calc_high[i]
                    stop_p = round_to_tick(sig_high + stop_ticks * tick_sz)
                    risk_amt = stop_p - entry_p
                    tp_p = round_to_tick(entry_p - risk_amt * rr)

                    if risk_amt > 0:
                        short_entries.iloc[i] = True
                        exec_prices.iloc[i] = entry_p
                        in_pos = True
                        pos_side = -1
                        entry_idx = i  # Store entry bar index
                        entry_price = entry_p
                        stop_price = stop_p
                        tp_price = tp_p
                        sl_dists.iloc[i] = risk_amt

        return long_entries, long_exits, short_entries, short_exits, exec_prices, sl_dists, exit_ratios
