"""
Event-driven trade simulator with intra-bar 1-minute resolution.

Replaces VectorBT for strategies that require:
  - Partial take-profit with breakeven moves
  - Intra-bar resolution (zoom to 1m data when multiple levels could be hit)
  - Auto-close at a configured time
  - Blackout windows (no new entries)

The simulator processes bars sequentially and manages full position lifecycle.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

BRUSSELS_TZ = "Europe/Brussels"
TP1_EXECUTION_TOUCH = "touch"
TP1_EXECUTION_BAR_CLOSE_IF_TOUCHED = "bar_close_if_touched"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class BlackoutWindow:
    active: bool = False
    start_hour: int = 0
    start_minute: int = 0
    end_hour: int = 0
    end_minute: int = 0


@dataclass
class SimulatorConfig:
    initial_equity: float = 50000.0
    risk_per_trade: float = 0.01
    max_contracts: int = 50
    tick_size: float = 0.25
    tick_value: float = 0.50
    point_value: float = 2.0
    fee_per_trade: float = 0.74

    auto_close_enabled: bool = True
    auto_close_hour: int = 21
    auto_close_minute: int = 0
    blackout_windows: List[BlackoutWindow] = field(default_factory=list)
    cooldown_bars: int = 0
    tp1_execution_mode: str = TP1_EXECUTION_TOUCH
    tp1_partial_pct: float = 0.25   # fraction of position to close at TP1
    tp2_partial_pct: float = 0.25   # fraction of position to close at TP2
    ema_exit_after_tp1_only: bool = False  # if True, EMA cross exit only fires after TP1
    no_sl_after_tp1: bool = False  # if True, intra-bar SL/BE disabled after TP1 (exit only via close-based logic)
    tp1_full_exit: bool = False          # if True, TP1 closes entire position (no partial); no breakeven move
    inverse_canal_exit: bool = False     # if True, LONG exits when close>upper, SHORT exits when close<lower

    daily_win_limit_enabled: bool = False
    daily_win_limit: float = 500.0
    daily_loss_limit_enabled: bool = False
    daily_loss_limit: float = 700.0


# ---------------------------------------------------------------------------
# Internal position state
# ---------------------------------------------------------------------------

@dataclass
class _Position:
    side: int  # 1=long, -1=short
    entry_price: float = 0.0
    entry_bar_time: str = ""
    entry_exec_time: str = ""
    stop_price: float = 0.0
    tp1_price: float = 0.0
    size: float = 1.0
    tp1_hit: bool = False
    tp2_hit: bool = False
    be_level: float = float('nan')   # breakeven trigger level (separate from TP1)
    be_hit: bool = False             # whether be_level was reached
    remaining_size: float = 1.0
    excluded: bool = False  # True if daily limit was reached before entry
    # Partial exit tracking
    partial_exits: List[Dict[str, Any]] = field(default_factory=list)
    # Supertrend trailing support
    tp2_price: float = float('nan')  # fixed TP2 price level
    initial_risk: float = 0.0        # risk distance at entry (for trailing activation)
    rr_trailing: float = 0.0         # R:R threshold for trailing activation
    trailing_active: bool = False     # whether trailing SL is active
    sl_buffer_st: float = 0.0        # buffer for Supertrend trailing SL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_brussels(ts: pd.Timestamp) -> pd.Timestamp:
    """Convert a timestamp to Brussels timezone."""
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert(BRUSSELS_TZ)


def _get_market_hour_offset(ts: pd.Timestamp) -> int:
    """Return the hour offset between standard and actual market session times.

    CME futures follow US/Eastern time.  When Brussels and US/Eastern are in
    the same DST state (both standard or both summer-time) the difference is
    6 h and the ``offset`` is **0** – session boundaries in Brussels are at
    their "reference" positions (Asia 00:00, UK 09:00, US 15:30 …).

    During the ~3-week spring window (US DST starts 2nd Sun March, EU last
    Sun March) and the ~1-week autumn window (EU DST ends last Sun October,
    US 1st Sun November) the difference drops to 5 h.  In that case every
    market-time boundary is 1 h **earlier** in Brussels, so ``offset = -1``.

    All configured session / blackout / auto-close times are expressed in the
    *reference* frame (offset 0).  To compare against real Brussels wall-clock
    time we shift the wall-clock by ``-offset`` (i.e. +1 h when offset = -1)
    so it lands back in the reference frame.
    """
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    utc_ts = ts.tz_convert("UTC")
    bxl_off_h = utc_ts.tz_convert(BRUSSELS_TZ).utcoffset().total_seconds() / 3600
    et_off_h = utc_ts.tz_convert("US/Eastern").utcoffset().total_seconds() / 3600
    diff = bxl_off_h - et_off_h
    return -1 if diff == 5 else 0


def _to_ref_minutes(ts: pd.Timestamp) -> int:
    """Convert a timestamp to reference-frame minutes-of-day (0-1439).

    Shifts the Brussels wall-clock time by ``-offset`` so that configured
    reference-frame boundaries can be compared directly.
    """
    bxl = _to_brussels(ts)
    offset_min = _get_market_hour_offset(ts) * 60
    return (bxl.hour * 60 + bxl.minute - offset_min) % 1440


def _is_in_time_slot(cur: int, sh: int, sm: int, eh: int, em: int) -> bool:
    start = sh * 60 + sm
    end = eh * 60 + em
    if start <= end:
        return cur >= start and cur < end
    else:
        return cur >= start or cur < end


def _is_blackout(ts: pd.Timestamp, windows: List[BlackoutWindow]) -> bool:
    ref = _to_ref_minutes(ts)
    for w in windows:
        if w.active and _is_in_time_slot(ref, w.start_hour, w.start_minute, w.end_hour, w.end_minute):
            return True
    return False


def _is_auto_close_bar(bar_time: pd.Timestamp, bar_close_time: pd.Timestamp,
                       ac_hour: int, ac_minute: int) -> bool:
    """Check if the auto-close time falls within this bar's time span.

    Both the bar boundaries and the target are expressed in reference-frame
    minutes so DST offsets cancel out.
    """
    open_ref = _to_ref_minutes(bar_time)
    close_ref = _to_ref_minutes(bar_close_time)
    target = ac_hour * 60 + ac_minute

    if close_ref >= open_ref:
        return target >= open_ref and target <= close_ref
    else:
        return target >= open_ref or target <= close_ref


def _matches_clock_time(ts: pd.Timestamp, hour: int, minute: int) -> bool:
    ref = _to_ref_minutes(ts)
    return ref // 60 == hour and ref % 60 == minute


def _get_session(ts: pd.Timestamp) -> str:
    ref = _to_ref_minutes(ts)
    if ref < 540:
        return "Asia"
    if ref < 930:
        return "UK"
    return "US"


def _round_tick(price: float, tick_size: float) -> float:
    if tick_size > 0:
        return round(price / tick_size) * tick_size
    return price


# ---------------------------------------------------------------------------
# Main simulation
# ---------------------------------------------------------------------------

def simulate(
    data: pd.DataFrame,
    data_1m: pd.DataFrame,
    signals: Dict[str, Any],
    config: SimulatorConfig,
    ema_main: pd.Series,
    ema_secondary: pd.Series,
) -> Dict[str, Any]:
    """
    Run an event-driven simulation.

    Parameters
    ----------
    data : DataFrame
        OHLCV at the backtest timeframe (e.g. 7m, 15m).
    data_1m : DataFrame
        1-minute OHLCV for intra-bar resolution.
    signals : dict
        Output from strategy.generate_signals():
            long_entries, short_entries (bool Series)
            sl_long, sl_short, tp1_long, tp1_short (float Series)
    config : SimulatorConfig
    ema_main : Series — main EMA for final exit
    ema_secondary : Series — secondary EMA for TP2

    Returns
    -------
    dict with keys: metrics, trades, equity_curve
    """

    idx = data.index
    n = len(data)

    np_open = data["Open"].values
    np_high = data["High"].values
    np_low = data["Low"].values
    np_close = data["Close"].values

    np_long_entry = signals["long_entries"].values
    np_short_entry = signals["short_entries"].values
    np_sl_long = signals["sl_long"].values
    np_sl_short = signals["sl_short"].values
    np_tp1_long = signals["tp1_long"].values
    np_tp1_short = signals["tp1_short"].values

    # Optional breakeven level signals (for strategies with pre-TP1 breakeven)
    _be_long_s = signals.get("be_long")
    _be_short_s = signals.get("be_short")
    np_be_long = _be_long_s.values if _be_long_s is not None else np.full(n, np.nan)
    np_be_short = _be_short_s.values if _be_short_s is not None else np.full(n, np.nan)

    # Optional custom entry price (for retracement entries)
    _ep_long_s = signals.get("entry_price_long")
    _ep_short_s = signals.get("entry_price_short")
    np_entry_price_long = _ep_long_s.values if _ep_long_s is not None else None
    np_entry_price_short = _ep_short_s.values if _ep_short_s is not None else None

    # Optional fixed TP2 price (instead of EMA-cross TP2)
    _tp2_long_s = signals.get("tp2_long")
    _tp2_short_s = signals.get("tp2_short")
    np_tp2_long = _tp2_long_s.values if _tp2_long_s is not None else None
    np_tp2_short = _tp2_short_s.values if _tp2_short_s is not None else None
    has_fixed_tp2 = np_tp2_long is not None or np_tp2_short is not None

    # Optional size-risk price override (for inverse strategies: size by TP distance, not SL distance)
    _sr_long_s = signals.get("size_risk_long")
    _sr_short_s = signals.get("size_risk_short")
    np_size_risk_long = _sr_long_s.values if _sr_long_s is not None else None
    np_size_risk_short = _sr_short_s.values if _sr_short_s is not None else None

    # Optional canal series (for HMA-canal-based exits instead of EMA cross)
    _canal_lower_s = signals.get("canal_lower")
    _canal_upper_s = signals.get("canal_upper")
    np_canal_lower = _canal_lower_s.values if _canal_lower_s is not None else None
    np_canal_upper = _canal_upper_s.values if _canal_upper_s is not None else None
    has_canal_exit = np_canal_lower is not None and np_canal_upper is not None

    # Optional Supertrend series (for trailing SL and reversal close)
    _st_s = signals.get("supertrend")
    _st_trend_s = signals.get("supertrend_trend")
    np_supertrend = _st_s.values if _st_s is not None else None
    np_st_trend = _st_trend_s.values if _st_trend_s is not None else None
    has_supertrend = np_supertrend is not None and np_st_trend is not None
    sig_rr_trailing = float(signals.get("rr_trailing", 0.0))
    sig_sl_buffer = float(signals.get("sl_buffer", 0.0))

    np_ema = ema_main.values
    np_ema2 = ema_secondary.values

    ts = config.tick_size
    tv = config.tick_value
    pv = config.point_value
    fee = config.fee_per_trade
    tp1_execution_mode = config.tp1_execution_mode

    if tp1_execution_mode not in {
        TP1_EXECUTION_TOUCH,
        TP1_EXECUTION_BAR_CLOSE_IF_TOUCHED,
    }:
        raise ValueError(f"Unsupported TP1 execution mode: {tp1_execution_mode}")

    inferred_bar_delta = (
        idx[1] - idx[0] if n > 1 else pd.Timedelta(minutes=1)
    )
    inferred_sub_bar_delta = (
        data_1m.index[1] - data_1m.index[0]
        if data_1m is not None and len(data_1m.index) > 1
        else pd.Timedelta(minutes=1)
    )

    # -----------------------------------------------------------------------
    # Pre-compute ref_minutes, timestamp strings, and Brussels dates
    # for all bars to avoid per-bar timezone conversions in the hot loop.
    # -----------------------------------------------------------------------
    _pre_ref_minutes = np.empty(n, dtype=np.int32)
    _pre_bar_time_str = [None] * n
    _pre_close_time_str = [None] * n
    _pre_brussels_dates = [None] * n

    for _i in range(n):
        _bt = idx[_i]
        _ct = idx[_i + 1] if _i + 1 < n else idx[_i] + inferred_bar_delta
        _pre_ref_minutes[_i] = _to_ref_minutes(_ct)
        _pre_bar_time_str[_i] = str(_bt)
        _pre_close_time_str[_i] = str(_ct)
        _pre_brussels_dates[_i] = str(_to_brussels(_ct).date())

    # Pre-compute auto-close bar flags
    _pre_is_auto_close = np.zeros(n, dtype=np.bool_)
    if config.auto_close_enabled:
        ac_target = config.auto_close_hour * 60 + config.auto_close_minute
        for _i in range(n):
            _open_ref = _to_ref_minutes(idx[_i])
            _close_ref = _pre_ref_minutes[_i]
            if _close_ref >= _open_ref:
                _pre_is_auto_close[_i] = ac_target >= _open_ref and ac_target <= _close_ref
            else:
                _pre_is_auto_close[_i] = ac_target >= _open_ref or ac_target <= _close_ref

    # Pre-compute blackout flags for entry logic
    _pre_is_blackout = np.zeros(n, dtype=np.bool_)
    if config.blackout_windows:
        for _i in range(n):
            ref = _pre_ref_minutes[_i]
            for w in config.blackout_windows:
                if w.active and _is_in_time_slot(ref, w.start_hour, w.start_minute, w.end_hour, w.end_minute):
                    _pre_is_blackout[_i] = True
                    break

    # Pre-index 1m data for fast sub-bar lookup via searchsorted
    _data_1m_index_values = None
    _data_1m_high = None
    _data_1m_low = None
    _data_1m_close = None
    if data_1m is not None and not data_1m.empty:
        _data_1m_index_values = data_1m.index.values  # numpy datetime64 array
        _data_1m_high = data_1m["High"].values
        _data_1m_low = data_1m["Low"].values
        _data_1m_close = data_1m["Close"].values

    # Position state
    pos: Optional[_Position] = None
    last_close_bar = -9999

    trades_list: List[Dict[str, Any]] = []
    equity = config.initial_equity
    equity_curve = [{"time": str(idx[0]), "value": equity}]

    # Daily limit tracking: cumulative PNL per Brussels date
    daily_pnl: Dict[str, float] = {}  # date_str -> cumulative PNL
    daily_limit_reached: Dict[str, bool] = {}  # date_str -> True if limit hit

    def _get_brussels_date(ts_str: str) -> str:
        ts = pd.Timestamp(ts_str)
        return str(_to_brussels(ts).date())

    def _check_daily_limit(date_str: str) -> bool:
        """Check if the daily limit has been reached for this date."""
        if date_str in daily_limit_reached:
            return True
        pnl = daily_pnl.get(date_str, 0.0)
        if config.daily_win_limit_enabled and pnl >= config.daily_win_limit:
            daily_limit_reached[date_str] = True
            return True
        if config.daily_loss_limit_enabled and pnl <= -config.daily_loss_limit:
            daily_limit_reached[date_str] = True
            return True
        return False

    # Pre-index 1m data by timestamp for fast lookup
    # We'll slice by time range when needed

    def _calc_size(entry_price: float, sl_price: float) -> float:
        risk_amount = config.initial_equity * config.risk_per_trade
        risk_dist = abs(entry_price - sl_price)
        if risk_dist <= 0:
            return 1.0
        risk_ticks = risk_dist / ts
        raw = risk_amount / (risk_ticks * tv)
        return float(min(config.max_contracts, max(1.0, int(raw))))

    def _close_position(exit_price: float, exit_bar_time: str, exit_exec_time: str, reason: str):
        nonlocal pos, equity
        if pos is None:
            return

        exit_price = _round_tick(exit_price, ts)

        # Calculate PnL for remaining size
        if pos.side == 1:
            pnl_points = exit_price - pos.entry_price
        else:
            pnl_points = pos.entry_price - exit_price

        gross_pnl = pnl_points * pos.remaining_size * pv
        total_fee = fee * pos.remaining_size

        # Add partial PnLs
        partial_gross = sum(p["gross_pnl"] for p in pos.partial_exits)
        partial_fees = sum(p["fee"] for p in pos.partial_exits)

        total_gross = gross_pnl + partial_gross
        total_fees = total_fee + partial_fees
        net_pnl = total_gross - total_fees

        is_excluded = pos.excluded
        if not is_excluded:
            equity += net_pnl
            # Update daily PNL tracking
            exit_date = _get_brussels_date(exit_exec_time)
            daily_pnl[exit_date] = daily_pnl.get(exit_date, 0.0) + net_pnl
            _check_daily_limit(exit_date)

        # Weighted avg exit price
        total_exit_weighted = exit_price * pos.remaining_size
        total_exit_size = pos.remaining_size
        for p in pos.partial_exits:
            total_exit_weighted += p["price"] * p["size"]
            total_exit_size += p["size"]
        avg_exit = total_exit_weighted / total_exit_size if total_exit_size > 0 else exit_price

        final_leg = {
            "entry_time": pos.entry_bar_time,
            "entry_execution_time": pos.entry_exec_time,
            "exit_time": exit_bar_time,
            "exit_execution_time": exit_exec_time,
            "side": "Long" if pos.side == 1 else "Short",
            "entry_price": pos.entry_price,
            "exit_price": exit_price,
            "pnl": gross_pnl - total_fee,
            "gross_pnl": gross_pnl,
            "fees": total_fee,
            "size": pos.remaining_size,
            "status": reason,
        }
        legs = [*pos.partial_exits, final_leg]

        trades_list.append({
            "entry_time": pos.entry_bar_time,
            "entry_execution_time": pos.entry_exec_time,
            "exit_time": exit_bar_time,
            "exit_execution_time": exit_exec_time,
            "side": "Long" if pos.side == 1 else "Short",
            "entry_price": pos.entry_price,
            "exit_price": avg_exit,
            "pnl": net_pnl,
            "gross_pnl": total_gross,
            "fees": total_fees,
            "size": pos.size,
            "pnl_pct": (net_pnl / config.initial_equity) * 100,
            "status": reason,
            "session": _get_session(pd.Timestamp(pos.entry_exec_time or pos.entry_bar_time)),
            "legs": legs,
            "excluded": is_excluded,
        })
        if not is_excluded:
            equity_curve.append({"time": exit_exec_time, "value": equity})

        pos = None

    def _get_partial_exit_size(ratio: float) -> float:
        if pos is None or pos.remaining_size <= 0:
            return 0.0

        if pos.remaining_size <= 1.0:
            return 0.0

        exit_size = math.floor(pos.size * ratio)
        if exit_size < 1 and pos.remaining_size >= 2.0:
            exit_size = 1
        if exit_size >= pos.remaining_size:
            exit_size = pos.remaining_size - 1.0
        if exit_size < 1:
            return 0.0
        return float(exit_size)

    def _partial_exit(
        price: float,
        ratio: float,
        label: str,
        exit_bar_time: str,
        exit_exec_time: str,
    ) -> float:
        """Execute a partial exit (TP1 or TP2) and return the exited size."""
        exit_size = _get_partial_exit_size(ratio)
        if exit_size <= 0:
            return 0.0

        price = _round_tick(price, ts)

        if pos.side == 1:
            pnl_pts = price - pos.entry_price
        else:
            pnl_pts = pos.entry_price - price

        gross = pnl_pts * exit_size * pv
        pos.partial_exits.append({
            "entry_time": pos.entry_bar_time,
            "entry_execution_time": pos.entry_exec_time,
            "exit_time": exit_bar_time,
            "exit_execution_time": exit_exec_time,
            "side": "Long" if pos.side == 1 else "Short",
            "entry_price": pos.entry_price,
            "price": price,
            "exit_price": price,
            "size": exit_size,
            "pnl": gross - fee * exit_size,
            "gross_pnl": gross,
            "fee": fee * exit_size,
            "fees": fee * exit_size,
            "status": label,
        })
        pos.remaining_size -= exit_size
        return float(exit_size)

    def _cross_under(current_a: float, current_b: float, prev_a: float, prev_b: float) -> bool:
        return (
            not np.isnan(current_a)
            and not np.isnan(current_b)
            and not np.isnan(prev_a)
            and not np.isnan(prev_b)
            and prev_a >= prev_b
            and current_a < current_b
        )

    def _cross_over(current_a: float, current_b: float, prev_a: float, prev_b: float) -> bool:
        return (
            not np.isnan(current_a)
            and not np.isnan(current_b)
            and not np.isnan(prev_a)
            and not np.isnan(prev_b)
            and prev_a <= prev_b
            and current_a > current_b
        )

    def _get_bar_close_time(bar_idx: int) -> pd.Timestamp:
        if bar_idx + 1 < n:
            return idx[bar_idx + 1]
        return idx[bar_idx] + inferred_bar_delta

    def _get_sub_bars(bar_time: pd.Timestamp, bar_close_time: pd.Timestamp) -> Optional[pd.DataFrame]:
        """Get 1-minute bars within a higher-TF bar's time span."""
        if _data_1m_index_values is None:
            return None

        start = bar_time
        end = bar_close_time

        # Align timezones
        if data_1m.index.tz is not None:
            if start.tzinfo is None:
                start = start.tz_localize(data_1m.index.tz)
            else:
                start = start.tz_convert(data_1m.index.tz)
            if end.tzinfo is None:
                end = end.tz_localize(data_1m.index.tz)
            else:
                end = end.tz_convert(data_1m.index.tz)

        # Use searchsorted for O(log n) lookup instead of boolean indexing
        start_np = np.datetime64(start)
        end_np = np.datetime64(end)
        i_start = np.searchsorted(_data_1m_index_values, start_np, side='left')
        i_end = np.searchsorted(_data_1m_index_values, end_np, side='left')

        if i_start >= i_end:
            return None
        return data_1m.iloc[i_start:i_end]

    def _update_supertrend_trailing(bar_idx: int):
        """Update position SL based on Supertrend trailing logic.

        Called once per higher-TF bar, before any exit checks.
        Handles trailing activation and SL ratcheting for strategies
        that provide a 'supertrend' series.
        """
        nonlocal pos
        if pos is None or not has_supertrend:
            return

        h = np_high[bar_idx]
        l = np_low[bar_idx]
        st_val = np_supertrend[bar_idx]
        if np.isnan(st_val):
            return

        st_trend_val = np_st_trend[bar_idx] if np_st_trend is not None else 0

        if pos.side == 1:
            # Check trailing activation (only when trend matches position side)
            if not pos.trailing_active and pos.initial_risk > 0:
                trail_trigger = pos.entry_price + pos.initial_risk * pos.rr_trailing
                if h >= trail_trigger:
                    pos.trailing_active = True
                    if st_trend_val == 1:
                        pos.stop_price = _round_tick(st_val - pos.sl_buffer_st, ts)

            # Update trailing SL (only ratchets up, only when trend is bullish)
            if pos.trailing_active and st_trend_val == 1:
                new_sl = _round_tick(st_val - pos.sl_buffer_st, ts)
                if pos.tp1_hit:
                    pos.stop_price = max(pos.stop_price, max(new_sl, pos.entry_price))
                else:
                    if new_sl > pos.stop_price:
                        pos.stop_price = new_sl
        else:
            # Check trailing activation (only when trend matches position side)
            if not pos.trailing_active and pos.initial_risk > 0:
                trail_trigger = pos.entry_price - pos.initial_risk * pos.rr_trailing
                if l <= trail_trigger:
                    pos.trailing_active = True
                    if st_trend_val == -1:
                        pos.stop_price = _round_tick(st_val + pos.sl_buffer_st, ts)

            # Update trailing SL (only ratchets down, only when trend is bearish)
            if pos.trailing_active and st_trend_val == -1:
                new_sl = _round_tick(st_val + pos.sl_buffer_st, ts)
                if pos.tp1_hit:
                    pos.stop_price = min(pos.stop_price, min(new_sl, pos.entry_price))
                else:
                    if new_sl < pos.stop_price:
                        pos.stop_price = new_sl

    def _process_touch_exit(
        bar_idx: int,
        h: float,
        l: float,
        exit_bar_time: str,
        exit_exec_time: str,
        tp1_touched_this_bar: bool,
        tp2_touched_this_bar: bool = False,
    ) -> tuple[bool, bool, bool]:
        """Process stop / TP1 / TP2 / BE events on a single price bar.

        Priority order matches PineScript: SL > TP1 > TP2 > BE level.
        Breakeven is active when any of: TP1 hit, TP1 touched this bar,
        or be_level reached (separate pre-TP1 breakeven trigger).
        For Supertrend strategies, breakeven is managed by the trailing logic.

        Returns (closed, tp1_touched_this_bar, tp2_touched_this_bar).
        """
        nonlocal pos

        if pos is None:
            return False, tp1_touched_this_bar, tp2_touched_this_bar

        # When no_sl_after_tp1 is set, disable all intra-bar SL/BE checks once
        # TP1 has been hit or touched on this bar. Position exits only via
        # close-based logic (canal exit, auto-close, end of data).
        if config.no_sl_after_tp1 and (pos.tp1_hit or tp1_touched_this_bar):
            return False, tp1_touched_this_bar, tp2_touched_this_bar

        # For Supertrend strategies, SL is already the effective SL (trailing
        # or breakeven handled by _update_supertrend_trailing).
        use_supertrend_sl = has_supertrend and pos.initial_risk > 0
        breakeven_active = pos.tp1_hit or pos.be_hit or tp1_touched_this_bar
        tp1_deferred_to_bar_close = (
            tp1_execution_mode == TP1_EXECUTION_BAR_CLOSE_IF_TOUCHED
        )

        if pos.side == 1:
            # 1. Check SL (effective price depends on breakeven/trailing state)
            if use_supertrend_sl:
                effective_sl = pos.stop_price
                sl_reason = "Trailing SL" if pos.trailing_active else "Stop Loss"
            else:
                effective_sl = pos.entry_price if breakeven_active else pos.stop_price
                sl_reason = "Breakeven" if breakeven_active else "Stop Loss"
            if l <= effective_sl:
                _close_position(effective_sl, exit_bar_time, exit_exec_time, sl_reason)
                return True, tp1_touched_this_bar, tp2_touched_this_bar

            # 2. Check TP1 (if not yet hit)
            if not pos.tp1_hit and not tp1_touched_this_bar and h >= pos.tp1_price:
                if tp1_deferred_to_bar_close:
                    tp1_touched_this_bar = True
                elif config.tp1_full_exit:
                    _close_position(pos.tp1_price, exit_bar_time, exit_exec_time, "TP")
                    return True, tp1_touched_this_bar, tp2_touched_this_bar
                else:
                    _partial_exit(
                        pos.tp1_price,
                        config.tp1_partial_pct,
                        "TP1",
                        exit_bar_time,
                        exit_exec_time,
                    )
                    if pos is not None:
                        pos.tp1_hit = True
                        if not use_supertrend_sl:
                            pos.stop_price = pos.entry_price
                    return pos is None, tp1_touched_this_bar, tp2_touched_this_bar

            # 3. Check TP2 at fixed price (if TP1 already hit or touched this bar)
            if (
                pos is not None
                and has_fixed_tp2
                and (pos.tp1_hit or tp1_touched_this_bar)
                and not pos.tp2_hit
                and not tp2_touched_this_bar
                and not np.isnan(pos.tp2_price)
                and h >= pos.tp2_price
            ):
                tp2_touched_this_bar = True

            # 4. Check BE level (separate pre-TP1 breakeven trigger)
            if (
                pos is not None
                and not use_supertrend_sl
                and not pos.tp1_hit
                and not pos.be_hit
                and not np.isnan(pos.be_level)
                and h >= pos.be_level
            ):
                pos.be_hit = True
                pos.stop_price = pos.entry_price
        else:
            # 1. Check SL
            if use_supertrend_sl:
                effective_sl = pos.stop_price
                sl_reason = "Trailing SL" if pos.trailing_active else "Stop Loss"
            else:
                effective_sl = pos.entry_price if breakeven_active else pos.stop_price
                sl_reason = "Breakeven" if breakeven_active else "Stop Loss"
            if h >= effective_sl:
                _close_position(effective_sl, exit_bar_time, exit_exec_time, sl_reason)
                return True, tp1_touched_this_bar, tp2_touched_this_bar

            # 2. Check TP1
            if not pos.tp1_hit and not tp1_touched_this_bar and l <= pos.tp1_price:
                if tp1_deferred_to_bar_close:
                    tp1_touched_this_bar = True
                elif config.tp1_full_exit:
                    _close_position(pos.tp1_price, exit_bar_time, exit_exec_time, "TP")
                    return True, tp1_touched_this_bar, tp2_touched_this_bar
                else:
                    _partial_exit(
                        pos.tp1_price,
                        config.tp1_partial_pct,
                        "TP1",
                        exit_bar_time,
                        exit_exec_time,
                    )
                    if pos is not None:
                        pos.tp1_hit = True
                        if not use_supertrend_sl:
                            pos.stop_price = pos.entry_price
                    return pos is None, tp1_touched_this_bar, tp2_touched_this_bar

            # 3. Check TP2 at fixed price (if TP1 already hit or touched this bar)
            if (
                pos is not None
                and has_fixed_tp2
                and (pos.tp1_hit or tp1_touched_this_bar)
                and not pos.tp2_hit
                and not tp2_touched_this_bar
                and not np.isnan(pos.tp2_price)
                and l <= pos.tp2_price
            ):
                tp2_touched_this_bar = True

            # 4. Check BE level
            if (
                pos is not None
                and not use_supertrend_sl
                and not pos.tp1_hit
                and not pos.be_hit
                and not np.isnan(pos.be_level)
                and l <= pos.be_level
            ):
                pos.be_hit = True
                pos.stop_price = pos.entry_price

        return False, tp1_touched_this_bar, tp2_touched_this_bar

    def _apply_tp1_at_bar_close(
        close_price: float,
        exit_bar_time: str,
        exit_exec_time: str,
    ):
        nonlocal pos

        if (
            pos is None
            or pos.tp1_hit
            or tp1_execution_mode != TP1_EXECUTION_BAR_CLOSE_IF_TOUCHED
        ):
            return

        _partial_exit(close_price, config.tp1_partial_pct, "TP1", exit_bar_time, exit_exec_time)
        if pos is not None:
            pos.tp1_hit = True
            use_supertrend_sl = has_supertrend and pos.initial_risk > 0
            if not use_supertrend_sl:
                pos.stop_price = pos.entry_price
            else:
                # For Supertrend strategies: SL = max/min(current SL, entry)
                if pos.side == 1:
                    pos.stop_price = max(pos.stop_price, pos.entry_price)
                else:
                    pos.stop_price = min(pos.stop_price, pos.entry_price)

    def _apply_tp2_at_bar_close(
        close_price: float,
        exit_bar_time: str,
        exit_exec_time: str,
    ):
        """Apply deferred TP2 at bar close price (like TP1 bar_close_if_touched)."""
        nonlocal pos
        if pos is None or pos.tp2_hit:
            return
        if not has_fixed_tp2:
            return

        _partial_exit(close_price, config.tp2_partial_pct, "TP2", exit_bar_time, exit_exec_time)
        if pos is not None:
            pos.tp2_hit = True

    def _process_sub_bars(
        bar_idx: int,
        bar_time: pd.Timestamp,
        bar_close_time: pd.Timestamp,
        sub_bars: pd.DataFrame,
    ) -> tuple[bool, bool, bool]:
        """
        Process intrabar stop/TP/BE events and exact auto-close on 1-minute bars.

        EMA-based exits stay on the higher timeframe close.
        Returns (closed, tp1_touched_this_bar, tp2_touched_this_bar).
        """
        nonlocal pos
        exit_bar_time = str(bar_time)
        tp1_touched_this_bar = False
        tp2_touched_this_bar = False

        for sub_i in range(len(sub_bars)):
            if pos is None:
                return True, tp1_touched_this_bar, tp2_touched_this_bar

            sub_h = sub_bars["High"].iloc[sub_i]
            sub_l = sub_bars["Low"].iloc[sub_i]
            sub_c = sub_bars["Close"].iloc[sub_i]
            sub_open_time = sub_bars.index[sub_i]
            sub_close_time = (
                sub_bars.index[sub_i + 1]
                if sub_i + 1 < len(sub_bars)
                else sub_open_time + inferred_sub_bar_delta
            )
            if sub_close_time > bar_close_time:
                sub_close_time = bar_close_time
            sub_exec_time = str(sub_close_time)

            closed_this_bar, tp1_touched_this_bar, tp2_touched_this_bar = _process_touch_exit(
                bar_idx,
                sub_h,
                sub_l,
                exit_bar_time,
                sub_exec_time,
                tp1_touched_this_bar,
                tp2_touched_this_bar,
            )
            if closed_this_bar:
                return True, tp1_touched_this_bar, tp2_touched_this_bar

            if (
                pos is not None
                and config.auto_close_enabled
                and _matches_clock_time(
                    sub_close_time,
                    config.auto_close_hour,
                    config.auto_close_minute,
                )
            ):
                in_profit = (sub_c > pos.entry_price) if pos.side == 1 else (sub_c < pos.entry_price)
                reason = "Auto-Close (profit)" if in_profit else "Auto-Close (loss)"
                _close_position(sub_c, exit_bar_time, sub_exec_time, reason)
                return True, tp1_touched_this_bar, tp2_touched_this_bar

        return pos is None, tp1_touched_this_bar, tp2_touched_this_bar

    def _process_close_based_exits(
        bar_idx: int,
        close_price: float,
        exit_bar_time: str,
        exit_exec_time: str,
    ) -> bool:
        """Process higher-timeframe close-based exits after intrabar events."""
        nonlocal pos

        if pos is None:
            return False

        # Supertrend reversal close: only before trailing activation AND before TP1
        # Matches PineScript states 5 (LONG_FULL) and 8 (SHORT_FULL)
        if has_supertrend and pos.initial_risk > 0:
            if not pos.trailing_active and not pos.tp1_hit:
                if pos.side == 1 and np_st_trend[bar_idx] != 1:
                    _close_position(close_price, exit_bar_time, exit_exec_time, "Supertrend Reversal")
                    return True
                elif pos.side == -1 and np_st_trend[bar_idx] != -1:
                    _close_position(close_price, exit_bar_time, exit_exec_time, "Supertrend Reversal")
                    return True

        # Canal-based exits (HMA channel): replaces EMA cross logic when present.
        # Normal: Long exits when close < canalLower, Short exits when close > canalUpper.
        # Inverse (inverse_canal_exit=True): Long exits when close > canalUpper, Short exits when close < canalLower.
        if has_canal_exit:
            cl = np_canal_lower[bar_idx] if bar_idx < len(np_canal_lower) else np.nan
            cu = np_canal_upper[bar_idx] if bar_idx < len(np_canal_upper) else np.nan
            if not np.isnan(cl) and not np.isnan(cu):
                if not config.inverse_canal_exit and not has_fixed_tp2 and config.tp2_partial_pct > 0 and pos.tp1_hit and not pos.tp2_hit:
                    inside_canal = close_price > cl and close_price < cu
                    if inside_canal:
                        exited = _partial_exit(close_price, config.tp2_partial_pct, "TP2_Canal", exit_bar_time, exit_exec_time)
                        if exited > 0:
                            pos.tp2_hit = True
                if pos is not None:
                    if config.inverse_canal_exit:
                        if pos.side == 1 and close_price > cu:
                            _close_position(close_price, exit_bar_time, exit_exec_time, "Canal Exit")
                            return True
                        elif pos.side == -1 and close_price < cl:
                            _close_position(close_price, exit_bar_time, exit_exec_time, "Canal Exit")
                            return True
                    else:
                        if pos.side == 1 and close_price < cl:
                            _close_position(close_price, exit_bar_time, exit_exec_time, "Canal Exit")
                            return True
                        elif pos.side == -1 and close_price > cu:
                            _close_position(close_price, exit_bar_time, exit_exec_time, "Canal Exit")
                            return True
            return pos is None

        ema_val = np_ema[bar_idx] if bar_idx < len(np_ema) else np.nan
        ema2_val = np_ema2[bar_idx] if bar_idx < len(np_ema2) else np.nan
        prev_close = np_close[bar_idx - 1] if bar_idx > 0 else np.nan
        prev_ema2 = np_ema2[bar_idx - 1] if bar_idx > 0 and bar_idx - 1 < len(np_ema2) else np.nan

        if pos.side == 1:
            # TP2: EMA-cross based (only when no fixed TP2 is provided)
            if not has_fixed_tp2 and config.tp2_partial_pct > 0:
                ema2_cross = _cross_under(close_price, ema2_val, prev_close, prev_ema2)
                if pos.tp1_hit and not pos.tp2_hit and ema2_cross and close_price > pos.entry_price:
                    exited_size = _partial_exit(close_price, config.tp2_partial_pct, "TP2_EMA", exit_bar_time, exit_exec_time)
                    if exited_size > 0:
                        pos.tp2_hit = True

            # EMA cross exit (optionally only after TP1; skipped if EMA is NaN)
            ema_exit_ok = not config.ema_exit_after_tp1_only or pos.tp1_hit
            if pos is not None and ema_exit_ok and not np.isnan(ema_val) and close_price < ema_val:
                _close_position(close_price, exit_bar_time, exit_exec_time, "EMA Cross")
                return True
        else:
            if not has_fixed_tp2 and config.tp2_partial_pct > 0:
                ema2_cross = _cross_over(close_price, ema2_val, prev_close, prev_ema2)
                if pos.tp1_hit and not pos.tp2_hit and ema2_cross and close_price < pos.entry_price:
                    exited_size = _partial_exit(close_price, config.tp2_partial_pct, "TP2_EMA", exit_bar_time, exit_exec_time)
                    if exited_size > 0:
                        pos.tp2_hit = True

            ema_exit_ok = not config.ema_exit_after_tp1_only or pos.tp1_hit
            if pos is not None and ema_exit_ok and not np.isnan(ema_val) and close_price > ema_val:
                _close_position(close_price, exit_bar_time, exit_exec_time, "EMA Cross")
                return True

        return pos is None

    # -----------------------------------------------------------------------
    # Main loop
    # -----------------------------------------------------------------------

    for i in range(n):
        bar_time = idx[i]
        bar_close_time = _get_bar_close_time(i)
        bar_time_str = _pre_bar_time_str[i]
        close_time_str = _pre_close_time_str[i]
        h = np_high[i]
        l = np_low[i]
        c = np_close[i]
        closed_this_bar = False
        tp1_touched_this_bar = False

        if pos is not None:
            # Update Supertrend trailing SL before exit checks
            _update_supertrend_trailing(i)

            tp2_touched_this_bar = False
            sub = _get_sub_bars(bar_time, bar_close_time)
            if sub is not None:
                closed_this_bar, tp1_touched_this_bar, tp2_touched_this_bar = _process_sub_bars(i, bar_time, bar_close_time, sub)
            else:
                closed_this_bar, tp1_touched_this_bar, tp2_touched_this_bar = _process_touch_exit(
                    i,
                    h,
                    l,
                    bar_time_str,
                    close_time_str,
                    False,
                    False,
                )

            if (
                pos is not None
                and not closed_this_bar
                and _pre_is_auto_close[i]
            ):
                in_profit = (c > pos.entry_price) if pos.side == 1 else (c < pos.entry_price)
                reason = "Auto-Close (profit)" if in_profit else "Auto-Close (loss)"
                _close_position(c, bar_time_str, close_time_str, reason)
                closed_this_bar = True

            if pos is not None and not closed_this_bar and tp1_touched_this_bar:
                _apply_tp1_at_bar_close(c, bar_time_str, close_time_str)

            # Apply deferred TP2 at bar close (touched during intra-bar or same bar as TP1)
            if pos is not None and not closed_this_bar and tp2_touched_this_bar:
                _apply_tp2_at_bar_close(c, bar_time_str, close_time_str)

            if pos is not None:
                closed_this_bar = (
                    _process_close_based_exits(i, c, bar_time_str, close_time_str) or closed_this_bar
                )

            if closed_this_bar or pos is None:
                last_close_bar = i

        # --- Entry logic ---
        if pos is None and not closed_this_bar:
            if _pre_is_blackout[i]:
                continue
            if (i - last_close_bar) < config.cooldown_bars:
                continue

            # Check if daily limit has been reached for this entry date
            entry_date = _pre_brussels_dates[i]
            entry_excluded = _check_daily_limit(entry_date)

            if np_long_entry[i]:
                # Use custom entry price if provided (e.g. retracement level)
                if np_entry_price_long is not None and not np.isnan(np_entry_price_long[i]):
                    entry_price = _round_tick(np_entry_price_long[i], ts)
                else:
                    entry_price = _round_tick(np_close[i], ts)
                sl_price = np_sl_long[i]
                tp1_price = np_tp1_long[i]
                if np.isnan(sl_price) or np.isnan(tp1_price):
                    continue

                risk_ref_long = (
                    np_size_risk_long[i]
                    if np_size_risk_long is not None and not np.isnan(np_size_risk_long[i])
                    else sl_price
                )
                size = _calc_size(entry_price, risk_ref_long)
                be_val = np_be_long[i]
                tp2_val = np_tp2_long[i] if np_tp2_long is not None else np.nan
                pos = _Position(
                    side=1,
                    entry_price=entry_price,
                    entry_bar_time=bar_time_str,
                    entry_exec_time=close_time_str,
                    stop_price=sl_price,
                    tp1_price=tp1_price,
                    be_level=be_val if not np.isnan(be_val) else float('nan'),
                    size=size,
                    remaining_size=size,
                    excluded=entry_excluded,
                    tp2_price=tp2_val if not np.isnan(tp2_val) else float('nan'),
                    initial_risk=abs(entry_price - sl_price) if has_supertrend else 0.0,
                    rr_trailing=sig_rr_trailing,
                    sl_buffer_st=sig_sl_buffer,
                )

            elif np_short_entry[i]:
                if np_entry_price_short is not None and not np.isnan(np_entry_price_short[i]):
                    entry_price = _round_tick(np_entry_price_short[i], ts)
                else:
                    entry_price = _round_tick(np_close[i], ts)
                sl_price = np_sl_short[i]
                tp1_price = np_tp1_short[i]
                if np.isnan(sl_price) or np.isnan(tp1_price):
                    continue

                risk_ref_short = (
                    np_size_risk_short[i]
                    if np_size_risk_short is not None and not np.isnan(np_size_risk_short[i])
                    else sl_price
                )
                size = _calc_size(entry_price, risk_ref_short)
                be_val = np_be_short[i]
                tp2_val = np_tp2_short[i] if np_tp2_short is not None else np.nan
                pos = _Position(
                    side=-1,
                    entry_price=entry_price,
                    entry_bar_time=bar_time_str,
                    entry_exec_time=close_time_str,
                    stop_price=sl_price,
                    tp1_price=tp1_price,
                    be_level=be_val if not np.isnan(be_val) else float('nan'),
                    size=size,
                    remaining_size=size,
                    excluded=entry_excluded,
                    tp2_price=tp2_val if not np.isnan(tp2_val) else float('nan'),
                    initial_risk=abs(sl_price - entry_price) if has_supertrend else 0.0,
                    rr_trailing=sig_rr_trailing,
                    sl_buffer_st=sig_sl_buffer,
                )

    # --- Close any remaining position at end of data ---
    if pos is not None:
        _close_position(np_close[-1], str(idx[-1]), str(_get_bar_close_time(n - 1)), "End of Data")

    # --- Compute metrics (only non-excluded trades) ---
    active_trades = [t for t in trades_list if not t.get("excluded", False)]
    total_trades = len(active_trades)
    winning = [t for t in active_trades if t["pnl"] > 0]
    win_rate = (len(winning) / total_trades * 100) if total_trades > 0 else 0.0
    cum_pnl = sum(t["pnl"] for t in active_trades)
    total_return = (cum_pnl / config.initial_equity) * 100

    # Max drawdown from equity curve
    eq_values = [p["value"] for p in equity_curve]
    peak = eq_values[0]
    max_dd = 0.0
    for v in eq_values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    # Sharpe approximation
    if len(trades_list) > 1:
        pnls = [t["pnl"] for t in trades_list]
        mean_pnl = np.mean(pnls)
        std_pnl = np.std(pnls)
        sharpe = (mean_pnl / std_pnl) * np.sqrt(252) if std_pnl > 0 else 0.0
    else:
        sharpe = 0.0

    metrics = {
        "total_return": float(total_return),
        "win_rate": float(win_rate),
        "total_trades": int(total_trades),
        "max_drawdown": float(max_dd * 100),
        "sharpe_ratio": float(sharpe),
    }

    # Build daily limit info: date → "win" or "loss"
    daily_limits_hit: Dict[str, str] = {}
    for date_str in daily_limit_reached:
        pnl = daily_pnl.get(date_str, 0.0)
        daily_limits_hit[date_str] = "win" if pnl >= 0 else "loss"

    return {
        "metrics": metrics,
        "trades": trades_list,
        "equity_curve": equity_curve,
        "daily_limits_hit": daily_limits_hit,
    }
