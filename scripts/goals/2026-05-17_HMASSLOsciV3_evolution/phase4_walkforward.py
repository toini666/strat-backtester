"""Phase 4 — walk-forward simple : split 50/50.

Split period 2025-01-06 → 2026-05-15 (~17 mois) en deux halves :
   - train : 2025-01-06 → 2025-10-10  (~9 mois — premier 50 %)
   - test  : 2025-10-10 → 2026-05-15  (~7 mois — second 50 %)

Pour chaque hypothèse KEEP du combo final, mesure :
  - baseline (Lab defaults) sur train et test
  - hypothèse activée sur train et test
  - delta de P/DD train vs test
Si une hypothèse améliore train mais dégrade test → rétrograder en MIXED.

⚠️ NOTE: la période full n'a que 17 mois — un split 50/50 donne 8-9 mois par fold.
Validation walk-forward LÉGÈRE (mission 7.A bonnes pratiques § "Walk-forward
même léger > rien").
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent / "phase2_hypotheses"))

from scripts.goals._shared.harness import run_backtest, summarize  # noqa: E402
from _shared import BASELINES, load_preset, preset_to_runargs  # noqa: E402

SPLIT = {
    "train": ("2025-01-06T00:00", "2025-10-10T00:00"),
    "test":  ("2025-10-10T00:00", "2026-05-15T00:00"),
}

# === MAJ après Phase 2 ====================================================
# Only MGC has KEEPs. MNQ has no winning hypothesis.
KEEP_HYPOTHESES: dict[str, list[tuple[str, object]]] = {
    "MGC_v3": [
        ("lab_entry_blocked_hours", (22, 20)),
        ("lab_disable_canal_exit_from_hour", 21),
    ],
}
# ==========================================================================


def fmt(s):
    return (
        f"PnL=${s['net_pnl']:>9,.0f} | DD=${s['max_dd_$']:>6,.0f} | "
        f"N={s['trades']:>4} | P/DD={s['net_pnl']/max(s['max_dd_$'],1):.2f}"
    )


def main():
    if not KEEP_HYPOTHESES:
        print("⚠️  KEEP_HYPOTHESES is empty — fill in after Phase 2 verdicts.")
        return
    for label, path in BASELINES.items():
        if label not in KEEP_HYPOTHESES:
            continue
        preset = load_preset(path)
        kwargs = preset_to_runargs(preset, strategy_name="HMASSLOsciV3Labv1")
        print(f"\n========== {label} walk-forward ==========")
        for fold, (start, end) in SPLIT.items():
            print(f"\n--- {fold} fold ({start} → {end}) ---")
            f_kwargs = dict(kwargs)
            f_kwargs["start"] = start
            f_kwargs["end"] = end
            base = summarize(run_backtest(**f_kwargs))
            print(f"  Baseline (defaults)   {fmt(base)}")
            for key, val in KEEP_HYPOTHESES[label]:
                hyp_kwargs = dict(f_kwargs)
                hyp_kwargs["strategy_params"] = {**kwargs["strategy_params"], key: val}
                hyp = summarize(run_backtest(**hyp_kwargs))
                marker = "↑" if (hyp["net_pnl"]/max(hyp["max_dd_$"],1)) > (base["net_pnl"]/max(base["max_dd_$"],1)) else "↓"
                print(f"  {key}={str(val):<10}  {marker} {fmt(hyp)}")
            # Full combo
            combo = dict(f_kwargs)
            combo["strategy_params"] = {**kwargs["strategy_params"]}
            for key, val in KEEP_HYPOTHESES[label]:
                combo["strategy_params"][key] = val
            r_combo = summarize(run_backtest(**combo))
            print(f"  COMBO all KEEP         {fmt(r_combo)}")


if __name__ == "__main__":
    main()
