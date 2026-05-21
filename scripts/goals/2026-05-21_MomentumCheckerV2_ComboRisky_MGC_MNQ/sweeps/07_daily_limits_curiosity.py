"""Phase 07 — Daily limits curiosity sweep (after_close mode).

User explicitly asked to test Max Daily Win / Max Daily Loss in after_close
mode out of curiosity. Compare to the no-limits baseline. Run on the
baseline preset (no other changes) so the lever effect is isolated.
"""
from __future__ import annotations

from _campaign import fmt_multi, run_multi  # noqa: E402

# (win_limit, win_enabled, loss_limit, loss_enabled, label)
CASES = [
    (500, False, 700, False, "baseline (no limits)"),
    (500, True,  700, True,  "+500 / -700 (preset defaults)"),
    (700, True,  500, True,  "+700 / -500 (asym, smaller-loss)"),
    (1000, True, 700, True,  "+1000 / -700"),
    (1500, True, 700, True,  "+1500 / -700"),
    (500, True,  1000, True, "+500 / -1000 (looser loss)"),
    (None, False, 500, True, "no win / -500 only"),
    (None, False, 700, True, "no win / -700 only"),
    (None, False, 1000, True, "no win / -1000 only"),
    (500, True,  None, False, "+500 only / no loss"),
    (1000, True, None, False, "+1000 only / no loss"),
]

if __name__ == "__main__":
    print("Daily limits sweep (after_close mode, both legs same limits):\n")
    for w, we, l, le, label in CASES:
        opts = {
            "daily_win_limit_enabled": we,
            "daily_win_limit": (w if w is not None else 0.0),
            "daily_loss_limit_enabled": le,
            "daily_loss_limit": (l if l is not None else 0.0),
            "daily_limit_mode": "after_close",
        }
        s = run_multi(
            engine_overrides_mgc=opts,
            engine_overrides_mnq=opts,
        )
        marker = " ✓" if s["max_dd_$"] < 2500 else ""
        print(f"  {label:<34s}  {fmt_multi(s)}{marker}")
