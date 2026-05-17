"""Phase 3 — combos par paires des hypothèses KEEP.

S'exécute après Phase 2. Lit les sweet spots KEEP de chaque hypothèse
(injectés en dur ci-dessous d'après les verdicts) et combine 2-à-2.

⚠️ Les sweet spots `KEEP_VALUES` sont MAJ après l'analyse Phase 2.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase2_hypotheses"))

from scripts.goals._shared.harness import run_backtest, summarize  # noqa: E402
from _shared import BASELINES, load_preset, preset_to_runargs, print_ab_header, print_ab_row  # noqa: E402


# === MAJ après Phase 2 ====================================================
# Only MGC has KEEPs. Both KEEP values are MGC-specific.
KEEP_VALUES: dict[str, dict | float | int | tuple] = {
    "lab_entry_blocked_hours": {"MGC_v3": (22, 20)},
    "lab_disable_canal_exit_from_hour": {"MGC_v3": 21},
}
# ==========================================================================


def get_value(key, label):
    v = KEEP_VALUES[key]
    if isinstance(v, dict):
        return v.get(label)  # None if not set for this asset
    return v


def has_all_keeps(label):
    """True if every KEEP_VALUES key has a value for this asset."""
    for k in KEEP_VALUES:
        if get_value(k, label) is None:
            return False
    return True


def main():
    if not KEEP_VALUES:
        print("⚠️  KEEP_VALUES is empty — fill in after Phase 2 verdicts.")
        print("Skipping pair combinations.")
        return
    print_ab_header("Phase 3 — pairs of KEEP hypotheses")
    keys = list(KEEP_VALUES.keys())
    for label, path in BASELINES.items():
        if not has_all_keeps(label):
            print(f"   [{label}] no KEEPs — skipping (see HYPOTHESES.md).")
            continue
        preset = load_preset(path)
        kwargs = preset_to_runargs(preset, strategy_name="HMASSLOsciV3Labv1")
        base_kwargs = dict(kwargs)
        r_base = summarize(run_backtest(**base_kwargs))
        base_pnl, base_dd, base_n = r_base["net_pnl"], r_base["max_dd_$"], r_base["trades"]
        print_ab_row(label, "OFF (baseline)", base_pnl, base_dd, base_n, base_pnl, base_dd, base_n)

        # Singletons first
        for k in keys:
            v = get_value(k, label)
            on_kwargs = dict(kwargs)
            on_kwargs["strategy_params"] = {**kwargs["strategy_params"], k: v}
            r_on = summarize(run_backtest(**on_kwargs))
            print_ab_row(label, f"ALONE {k.replace('lab_','')}={v}",
                         r_on["net_pnl"], r_on["max_dd_$"], r_on["trades"],
                         base_pnl, base_dd, base_n)

        # Then pairs
        for k1, k2 in itertools.combinations(keys, 2):
            v1 = get_value(k1, label)
            v2 = get_value(k2, label)
            on_kwargs = dict(kwargs)
            on_kwargs["strategy_params"] = {
                **kwargs["strategy_params"],
                k1: v1,
                k2: v2,
            }
            r_on = summarize(run_backtest(**on_kwargs))
            tag = f"PAIR {k1.replace('lab_','')[:10]}+{k2.replace('lab_','')[:10]}"
            print_ab_row(label, tag[:32],
                         r_on["net_pnl"], r_on["max_dd_$"], r_on["trades"],
                         base_pnl, base_dd, base_n)
        print()


if __name__ == "__main__":
    main()
