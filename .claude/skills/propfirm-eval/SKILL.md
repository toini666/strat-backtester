---
name: propfirm-eval
description: "Estimate prop-firm evaluation pass/fail rate and durations for any saved preset. Replays the preset, walks the resulting trade stream through a Topstep-style $50k Combine ($3k profit target, $2k trailing DD that locks at $0 PnL, $1.5k daily profit cap), and reports per-day-start and sequential pass rates plus average/median times. Trigger when the user wants to know how often a preset would pass a prop-firm evaluation, in how long, or with `/propfirm-eval`."
trigger: /propfirm-eval
---

# /propfirm-eval

Replays a saved backtest preset and simulates **prop-firm evaluation attempts** on top of the resulting trade stream. Answers the question: *"If I had started an evaluation every day with this preset, how many would have passed, and how long would they have taken?"*

## Default rules (Topstep $50k Combine)

| Rule | Default |
|---|---|
| Profit target (PASS) | **$3,000** cumulative PnL |
| Trailing drawdown | **$2,000** from peak — `floor = min(start_equity, peak − 2,000)` |
| Floor lock | Once peak hits start + $2,000, floor locks at **start_equity ($0 PnL)** permanently |
| Daily PnL cap | **$1,500** max PROFIT per Brussels calendar day. The capping trade's contribution is truncated to bring the day exactly to $1,500 and all remaining trades that day are skipped |

All four are CLI-overridable for other prop firms.

## Usage

```bash
# default analysis (both daily-start + sequential)
python scripts/propfirm_eval.py "Preset Name"

# fuzzy match works if the substring is unique
python scripts/propfirm_eval.py "MomentumCheckerV2"

# only the daily-start view
python scripts/propfirm_eval.py "Preset Name" --mode daily

# only the sequential view (each new eval starts at the next trade after a result)
python scripts/propfirm_eval.py "Preset Name" --mode sequential

# different prop-firm template
python scripts/propfirm_eval.py "Preset" --target 5000 --dd-limit 2500 --daily-cap 0

# list every saved preset
python scripts/propfirm_eval.py --list
```

Works for `mode: single`, `mode: multi_asset`, and `mode: multi_strat` presets — the script auto-dispatches and merges the legs.

## Two analyses

- **Daily-start** — one fresh evaluation begins at the first trade of every Brussels date that has at least one trade. Each eval walks forward independently. Best estimate of *"what if I had started today?"*.
- **Sequential** — one evaluation starts at the first trade; on pass or fail, the next starts at the very next trade. Best estimate of *"how many evaluations could this preset have run back-to-back?"*.

Both reports give: total / pass / fail / pending counts, pass rate (with and without pending), and duration stats (mean, median, fastest, slowest, average active days, average trades).

## Implementation notes

- The script delegates the backtest to `scripts/goals/_shared/harness.run_backtest`, so it inherits the UI-default engine settings per strategy — the trade stream is identical to what the UI would produce for that preset.
- The eval rules are layered on top of the simulator output: the preset's own `daily_win_limit` / `daily_loss_limit` (if set) are respected (excluded trades stay excluded), then the propfirm rules apply on the active trades.
- A trade is treated as a single PnL unit realized at `exit_time` — partial-leg PnL within a single trade is not split across day boundaries.
- Timezone: trade times are coerced to Europe/Brussels for the "calendar day" key.
