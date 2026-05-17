"""H-A4 — `lab_entry_blocked_hours` : bloque des heures toxiques spécifiques au-delà
des blackouts engine.

Source obs : obs-A2b.
- MNQ : H=6 (PnL −$2,112, WR 30.8%, SL rate 53.8%, n=52)
- MGC : H=22 (PnL −$891, WR 33%, SL rate 67%, n=9)

Pour chaque preset on teste les heures candidates de SON own profil de toxicité.
Le param est une liste — donc 1 sweep par preset avec sa propre liste.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize  # noqa: E402

from _shared import BASELINES, load_preset, preset_to_runargs, print_ab_header, print_ab_row  # noqa: E402


# Asset-specific blocked-hour candidates derived from Phase 1 hour analysis.
CANDIDATES = {
    "MNQ_v5": [
        (),                # OFF
        (6,),              # H=6 only
        (6, 12),           # +residual H=12
        (6, 4),            # +H=4 (residual marginal)
        (6, 12, 4),
    ],
    "MGC_v3": [
        (),                # OFF
        (22,),             # H=22 only
        (22, 20),          # +H=20 marginal
        (22, 17),          # +H=17 marginal
        (22, 20, 17),
    ],
}


def main():
    print_ab_header("H-A4 lab_entry_blocked_hours")
    for label, path in BASELINES.items():
        preset = load_preset(path)
        kwargs = preset_to_runargs(preset, strategy_name="HMASSLOsciV3Labv1")
        candidates = CANDIDATES[label]
        # Run OFF first to establish baseline
        base_kwargs = dict(kwargs)
        base_kwargs["strategy_params"] = {**kwargs["strategy_params"], "lab_entry_blocked_hours": ()}
        r_base = summarize(run_backtest(**base_kwargs))
        base_pnl, base_dd, base_n = r_base["net_pnl"], r_base["max_dd_$"], r_base["trades"]
        print_ab_row(label, "OFF (=())", base_pnl, base_dd, base_n, base_pnl, base_dd, base_n)

        for hours in candidates:
            if not hours:
                continue  # skip duplicate OFF
            on_kwargs = dict(kwargs)
            on_kwargs["strategy_params"] = {**kwargs["strategy_params"], "lab_entry_blocked_hours": hours}
            r_on = summarize(run_backtest(**on_kwargs))
            label_str = "ON " + ",".join(str(h) for h in hours)
            print_ab_row(label, label_str,
                         r_on["net_pnl"], r_on["max_dd_$"], r_on["trades"],
                         base_pnl, base_dd, base_n)
        print()


if __name__ == "__main__":
    main()
