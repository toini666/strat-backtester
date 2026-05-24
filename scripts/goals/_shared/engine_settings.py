"""UI-mirror engine defaults — keep in sync with the frontend.

⚠️ Source of truth is the frontend. If you change a default there, change it here.
   - Frontend base defaults:        frontend/src/api.ts (DEFAULT_BACKTEST_ENGINE_SETTINGS)
   - Per-strategy UI overrides:     frontend/src/App.tsx (STRATEGY_ENGINE_OVERRIDES)

The functions below give you the EXACT engine settings the UI would send
to the backend when a strategy is first selected — without any user edits.
A goal harness must build off these to produce results reproducible in the UI.
"""

from __future__ import annotations

from typing import Iterable, Optional

from backend.api import BacktestEngineSettings, BlackoutWindowSettings


# Frontend DEFAULT_BACKTEST_ENGINE_SETTINGS — frontend/src/api.ts
_FRONTEND_BASE_BLACKOUTS = [
    {"active": False, "start_hour": 0,  "start_minute": 0,  "end_hour": 0,  "end_minute": 5},
    {"active": False, "start_hour": 9,  "start_minute": 0,  "end_hour": 9,  "end_minute": 5},
    {"active": True,  "start_hour": 12, "start_minute": 0,  "end_hour": 14, "end_minute": 0},
    {"active": False, "start_hour": 15, "start_minute": 30, "end_hour": 15, "end_minute": 35},
    {"active": True,  "start_hour": 16, "start_minute": 30, "end_hour": 22, "end_minute": 0},
    {"active": True,  "start_hour": 22, "start_minute": 0,  "end_hour": 23, "end_minute": 59},
]
_FRONTEND_BASE_AUTO_CLOSE = (22, 0)


# Frontend STRATEGY_ENGINE_OVERRIDES — frontend/src/App.tsx
# Only blackout overrides are defined per strategy at the moment.
_STRATEGY_OVERRIDES: dict[str, dict] = {
    "HMASSLOsciV2": {
        "blackout_windows": [
            {"active": False, "start_hour": 0,  "start_minute": 0,  "end_hour": 0,  "end_minute": 5},
            {"active": False, "start_hour": 9,  "start_minute": 0,  "end_hour": 9,  "end_minute": 5},
            {"active": False, "start_hour": 12, "start_minute": 0,  "end_hour": 14, "end_minute": 0},
            {"active": False, "start_hour": 15, "start_minute": 30, "end_hour": 15, "end_minute": 35},
            {"active": False, "start_hour": 16, "start_minute": 30, "end_hour": 22, "end_minute": 0},
            {"active": True,  "start_hour": 22, "start_minute": 0,  "end_hour": 23, "end_minute": 59},
        ],
    },
    "HMASSLOsciV3": {
        "blackout_windows": [
            {"active": False, "start_hour": 0,  "start_minute": 0,  "end_hour": 0,  "end_minute": 5},
            {"active": False, "start_hour": 9,  "start_minute": 0,  "end_hour": 9,  "end_minute": 5},
            {"active": False, "start_hour": 12, "start_minute": 0,  "end_hour": 14, "end_minute": 0},
            {"active": False, "start_hour": 15, "start_minute": 30, "end_hour": 15, "end_minute": 35},
            {"active": False, "start_hour": 16, "start_minute": 30, "end_hour": 22, "end_minute": 0},
            {"active": True,  "start_hour": 22, "start_minute": 0,  "end_hour": 23, "end_minute": 59},
        ],
    },
    "HMASSLOsciV4": {
        "blackout_windows": [
            {"active": False, "start_hour": 0,  "start_minute": 0,  "end_hour": 0,  "end_minute": 5},
            {"active": False, "start_hour": 9,  "start_minute": 0,  "end_hour": 9,  "end_minute": 5},
            {"active": False, "start_hour": 12, "start_minute": 0,  "end_hour": 14, "end_minute": 0},
            {"active": False, "start_hour": 15, "start_minute": 30, "end_hour": 15, "end_minute": 35},
            {"active": False, "start_hour": 16, "start_minute": 30, "end_hour": 22, "end_minute": 0},
            {"active": True,  "start_hour": 22, "start_minute": 0,  "end_hour": 23, "end_minute": 59},
        ],
    },
    "GatorMTFv4": {
        "blackout_windows": [
            {"active": False, "start_hour": 8,  "start_minute": 0,  "end_hour": 8,  "end_minute": 5},
            {"active": False, "start_hour": 11, "start_minute": 0,  "end_hour": 13, "end_minute": 0},
            {"active": False, "start_hour": 14, "start_minute": 30, "end_hour": 14, "end_minute": 35},
            {"active": False, "start_hour": 16, "start_minute": 0,  "end_hour": 20, "end_minute": 0},
            {"active": False, "start_hour": 21, "start_minute": 0,  "end_hour": 23, "end_minute": 0},
            {"active": True,  "start_hour": 22, "start_minute": 0,  "end_hour": 23, "end_minute": 59},
        ],
    },
}


def ui_default_engine_settings(strategy_name: str) -> BacktestEngineSettings:
    """Return the engine settings the UI would build when this strategy is first selected.

    Use this as the baseline for any campaign harness. Then mutate (activate
    blackouts, add windows, enable daily limits, etc.) to test variants.
    """
    blackouts_raw = _STRATEGY_OVERRIDES.get(strategy_name, {}).get(
        "blackout_windows", _FRONTEND_BASE_BLACKOUTS
    )
    auto_close = _STRATEGY_OVERRIDES.get(strategy_name, {}).get(
        "auto_close", _FRONTEND_BASE_AUTO_CLOSE
    )
    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=auto_close[0],
        auto_close_minute=auto_close[1],
        blackout_windows=[BlackoutWindowSettings(**w) for w in blackouts_raw],
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=500.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def make_engine_settings(
    strategy_name: str,
    *,
    auto_close_hour: Optional[int] = None,
    auto_close_minute: Optional[int] = None,
    extra_active_windows: Iterable[dict] = (),
    activate_existing: Iterable[tuple[int, int, int, int]] = (),
    daily_win_limit: Optional[float] = None,
    daily_loss_limit: Optional[float] = None,
    daily_limit_mode: str = "after_close",
) -> BacktestEngineSettings:
    """Convenience builder on top of `ui_default_engine_settings`.

    Args:
        strategy_name:        e.g. "HMASSLOsciV3" — picks the right UI overrides
        auto_close_hour/min:  override (reference Brussels time)
        extra_active_windows: list of dicts {start_hour, start_minute, end_hour, end_minute}
                              appended as ACTIVE blackouts (in addition to existing ones)
        activate_existing:    list of (start_h, start_m, end_h, end_m) — flip an
                              EXISTING window from inactive→active
        daily_win_limit:      if set, enables the daily win cap with this $ value
        daily_loss_limit:     same for loss
        daily_limit_mode:     "after_close" (default) | "intra_bar"
    """
    es = ui_default_engine_settings(strategy_name)
    if auto_close_hour is not None:
        es.auto_close_hour = auto_close_hour
    if auto_close_minute is not None:
        es.auto_close_minute = auto_close_minute

    for sh, sm, eh, em in activate_existing:
        for w in es.blackout_windows:
            if (w.start_hour, w.start_minute, w.end_hour, w.end_minute) == (sh, sm, eh, em):
                w.active = True
                break

    for w in extra_active_windows:
        es.blackout_windows.append(BlackoutWindowSettings(active=True, **w))

    if daily_win_limit is not None:
        es.daily_win_limit_enabled = True
        es.daily_win_limit = float(daily_win_limit)
    if daily_loss_limit is not None:
        es.daily_loss_limit_enabled = True
        es.daily_loss_limit = float(daily_loss_limit)
    es.daily_limit_mode = daily_limit_mode
    return es
