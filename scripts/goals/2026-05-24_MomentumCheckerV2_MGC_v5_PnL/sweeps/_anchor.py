"""Current anchor for v5 PnL campaign (updated as sweeps converge)."""

from _campaign import SEED_PARAMS, SEED_RISK_PCT, build_engine_settings


# Phase-5 anchor: best BO surgery so far
# PnL $37,689 / DD $2,066 / WR 52.5 % / N=1048 (10.5s)
ANCHOR_BOS = [
    (12, 0, 12, 30),
    (12, 30, 14, 0),
    (15, 30, 17, 0),
    (18, 0, 19, 0),
    (20, 0, 21, 0),
    (2, 0, 3, 0),
    (6, 30, 7, 0),
    (11, 30, 12, 0),
    (19, 30, 20, 0),
]
ANCHOR_PARAMS = dict(SEED_PARAMS)
# Phase-8 upgrade: ema_prin_len 30 -> 40 (+$844 PnL, -$15 DD).
ANCHOR_PARAMS["ema_prin_len"] = 40
# Phase-9/10 alligator + HMA wins: lips_length=6, lips_offset=5, hma2_len=76.
# Combined: +$6,901 PnL, -$117 DD vs ema_prin=40 only.
ANCHOR_PARAMS["lips_length"] = 6
ANCHOR_PARAMS["lips_offset"] = 5
ANCHOR_PARAMS["hma2_len"] = 76
# Phase-11 win: sl_max_points 120 -> 80 (+$1,254 PnL, same DD).
ANCHOR_PARAMS["sl_max_points"] = 80.0
ANCHOR_RISK = SEED_RISK_PCT  # 0.42 %


def anchor_engine_settings():
    return build_engine_settings(blackouts=ANCHOR_BOS, auto_close_h=22,
                                 auto_close_m=0)


def anchor_kwargs(params_override=None, risk=None, engine_settings=None):
    from _campaign import seed_kwargs
    p = dict(ANCHOR_PARAMS)
    if params_override:
        p.update(params_override)
    if engine_settings is None:
        engine_settings = anchor_engine_settings()
    return seed_kwargs(
        params=p,
        risk_per_trade=risk if risk is not None else ANCHOR_RISK,
        engine_settings=engine_settings,
    )
