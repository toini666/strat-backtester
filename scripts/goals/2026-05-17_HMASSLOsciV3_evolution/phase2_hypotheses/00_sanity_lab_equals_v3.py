"""00 — Sanity test: HMASSLOsciV3Labv1 with all flags at defaults == HMASSLOsciV3.

Reproduces both baseline winners (MNQ_v5, MGC_v3) using the Lab strategy and
verifies PnL and DD match within a tight tolerance (~$10).

If this fails, STOP and debug the Lab class. Subsequent hypothesis sweeps
would be uninterpretable because the OFF baseline differs from V3.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import bench  # noqa: E402
from scripts.goals._shared.preset import replay_preset  # noqa: E402

from _shared import BASELINES, BASELINE_METRICS, load_preset, preset_to_runargs  # noqa: E402

TOL_PNL = 10.0
TOL_DD = 10.0


def main() -> int:
    print(f"Sanity test — HMASSLOsciV3Labv1(defaults) must reproduce HMASSLOsciV3")
    print("=" * 90)
    all_ok = True
    for label, preset_path in BASELINES.items():
        preset = load_preset(preset_path)
        kwargs = preset_to_runargs(preset)  # uses preset["strategyName"]=V3

        # 1) Original V3 — replay reference to lock the expected metrics
        ref = bench(f"{label} V3 (reference)", **kwargs)

        # 2) Lab v1 with the SAME params but the new strategy name
        kwargs_lab = dict(kwargs)
        kwargs_lab["strategy_name"] = "HMASSLOsciV3Labv1"
        lab = bench(f"{label} Lab(defaults)", **kwargs_lab)

        dpnl = lab["net_pnl"] - ref["net_pnl"]
        ddd = lab["max_dd_$"] - ref["max_dd_$"]
        dn = lab["trades"] - ref["trades"]
        match = abs(dpnl) <= TOL_PNL and abs(ddd) <= TOL_DD and dn == 0
        flag = "✅" if match else "❌"
        print(
            f"   {flag} {label}: ΔPnL=${dpnl:+,.2f}  ΔDD=${ddd:+,.2f}  ΔN={dn:+d}"
        )

        # Also cross-check against published metrics (catches preset drift)
        exp = BASELINE_METRICS[label]
        dpnl_exp = ref["net_pnl"] - exp["pnl"]
        ddd_exp = ref["max_dd_$"] - exp["dd"]
        print(
            f"      vs published REPORT.md   : ΔPnL=${dpnl_exp:+,.2f}  ΔDD=${ddd_exp:+,.2f}"
        )

        if not match:
            all_ok = False

    print("=" * 90)
    if all_ok:
        print("✅ SANITY PASS — Lab(defaults) reproduces V3 exactly on both baselines.")
        return 0
    print("❌ SANITY FAIL — investigate Lab class before running any hypothesis sweep.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
