"""HMA-SSL-Osci V3 — exit lab.

Subclass de HMASSLOsciV3 dédiée à l'évolution du mécanisme de sortie
(final exit + partial). Tous les nouveaux paramètres ont un default qui
reproduit le comportement V3 exact — la stratégie Lab sans aucun flag
activé = V3 strict (vérifié par phase2_hypotheses/00_sanity_lab_equals_v3.py).

Conventions :
- Préfixe ``lab_exit_`` pour les flags du levier EX (trigger de sortie finale).
- Préfixe ``lab_pt_`` pour les flags du levier PT (partial take-profit).
- Default = neutralité (False, 0, 0.0).
- Un helper privé ``_apply_<hyp_name>()`` par hypothèse, indépendant et désactivable.

Les hypothèses opèrent UNIQUEMENT sur les séries consommées par le simulateur
(``hw_cross_over/under``, ``fast_hma_exit_long/short``, ``partial_close_long/short``)
et n'introduisent JAMAIS de nouvelle entrée. Le simulateur n'est pas modifié.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from .hma_ssl_osci_v3 import HMASSLOsciV3


class HMASSLOsciV3LabExitV1(HMASSLOsciV3):
    name = "HMASSLOsciV3LabExitV1"

    default_params = {
        **HMASSLOsciV3.default_params,
        # === Levier EX (trigger de sortie finale) ============================
        # H1 — sortir directement au cross HMA rapide, sans attendre la HW
        "lab_exit_fast_cross_only": False,
        # H2 — attendre la HW (V3 default) mais ne sortir que si in-profit au HW
        "lab_exit_hw_only_if_profit": False,
        # H3 — sortir sur flip du canal HMA (contra-direction)
        "lab_exit_on_canal_flip": False,
        # H4 — MFE-floor : fermer une fois MFE atteint puis retombé sous Y R
        "lab_exit_mfe_floor_r": 0.0,
        "lab_exit_mfe_floor_trigger_r": 0.0,
        # H5 — time-based : forcer la sortie au fast cross si N bars depuis entrée
        "lab_exit_fast_cross_after_bars": 0,
        # === Levier PT (partial take-profit) =================================
        # H6 — partial X% sur cross HMA rapide
        "lab_pt_on_fast_cross_pct": 0.0,
        # H7 — partial X% sur flip canal HMA
        "lab_pt_on_canal_flip_pct": 0.0,
        # H8 — partial X% sur MFE seuil
        "lab_pt_on_mfe_r_pct": 0.0,
        "lab_pt_on_mfe_r_trigger": 0.0,
    }

    param_ranges = {
        **HMASSLOsciV3.param_ranges,
        "lab_exit_fast_cross_only": [False, True],
        "lab_exit_hw_only_if_profit": [False, True],
        "lab_exit_on_canal_flip": [False, True],
        "lab_exit_mfe_floor_r": [0.0, 0.3, 0.5, 0.8, 1.0, 1.5],
        "lab_exit_mfe_floor_trigger_r": [0.0, 0.5, 1.0, 1.5, 2.0],
        "lab_exit_fast_cross_after_bars": [0, 5, 10, 15, 20],
        "lab_pt_on_fast_cross_pct": [0.0, 25.0, 50.0, 75.0],
        "lab_pt_on_canal_flip_pct": [0.0, 25.0, 50.0],
        "lab_pt_on_mfe_r_pct": [0.0, 25.0, 50.0],
        "lab_pt_on_mfe_r_trigger": [0.0, 0.5, 1.0, 1.5, 2.0],
    }

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #

    def generate_signals(self, data: pd.DataFrame,
                         params: Dict[str, Any] = None) -> Dict[str, Any]:
        p = self.get_params(params)
        result = super().generate_signals(data, p)

        # Snapshot V3-native series (the "OFF" reference) so each helper can
        # base its modifications on the unmodified V3 baseline if needed.
        # (Currently helpers mutate result in place, but keeping the contract
        # for future helpers that might need V3-vs-current comparisons.)

        # Levier EX — order matters when several flags ON: harder overrides
        # (fast_cross_only, canal_flip) executed first so later hypotheses
        # see the augmented series.
        if p.get("lab_exit_fast_cross_only"):
            self._apply_exit_fast_cross_only(result, data, p)
        if p.get("lab_exit_hw_only_if_profit"):
            self._apply_exit_hw_only_if_profit(result, data, p)
        if p.get("lab_exit_on_canal_flip"):
            self._apply_exit_on_canal_flip(result, data, p)
        if float(p.get("lab_exit_mfe_floor_r", 0.0)) > 0:
            self._apply_exit_mfe_floor(result, data, p)
        if int(p.get("lab_exit_fast_cross_after_bars", 0)) > 0:
            self._apply_exit_fast_cross_after_bars(result, data, p)

        # Levier PT — partials cumulés dans partial_close_long/short.
        if float(p.get("lab_pt_on_fast_cross_pct", 0.0)) > 0:
            self._apply_pt_on_fast_cross(result, data, p)
        if float(p.get("lab_pt_on_canal_flip_pct", 0.0)) > 0:
            self._apply_pt_on_canal_flip(result, data, p)
        if float(p.get("lab_pt_on_mfe_r_pct", 0.0)) > 0:
            self._apply_pt_on_mfe(result, data, p)

        return result

    def get_simulator_settings(self, params=None):
        p = self.get_params(params)
        s = super().get_simulator_settings(p)

        # If any "full close via partial" hypothesis is active OR any PT
        # partial is active, tp1_partial_pct overrides hw_partial_pct.
        # Priority: 100% close (full-exit hypotheses) wins; otherwise take
        # the max of PT percentages.
        pt_pct = 0.0
        if p.get("lab_exit_hw_only_if_profit"):
            pt_pct = 1.0
        if float(p.get("lab_exit_mfe_floor_r", 0.0)) > 0:
            pt_pct = 1.0
        if float(p.get("lab_pt_on_fast_cross_pct", 0.0)) > 0:
            pt_pct = max(pt_pct, float(p["lab_pt_on_fast_cross_pct"]) / 100.0)
        if float(p.get("lab_pt_on_canal_flip_pct", 0.0)) > 0:
            pt_pct = max(pt_pct, float(p["lab_pt_on_canal_flip_pct"]) / 100.0)
        if float(p.get("lab_pt_on_mfe_r_pct", 0.0)) > 0:
            pt_pct = max(pt_pct, float(p["lab_pt_on_mfe_r_pct"]) / 100.0)
        if pt_pct > 0:
            s["tp1_partial_pct"] = pt_pct

        return s

    # ------------------------------------------------------------------ #
    # Levier EX helpers                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _as_bool_array(series: pd.Series) -> np.ndarray:
        return series.values.astype(bool, copy=True)

    @staticmethod
    def _or_bool_series(result: Dict[str, Any], key: str,
                        extra: np.ndarray, index: pd.Index) -> None:
        existing = result.get(key)
        if existing is None:
            result[key] = pd.Series(extra, index=index)
            return
        merged = existing.values.astype(bool) | extra
        result[key] = pd.Series(merged, index=index)

    def _apply_exit_fast_cross_only(self, result, data, p):
        """H1 — Skip HW confirmation.

        Injects hw_cross_over/under at fast_hma_exit_long/short bars so the
        V3 simulator's ``pending_final_exit + hw_cross_any`` chain fires on
        the same bar. The ``block_loss_canal_exit_before_tp1`` V3 setting
        still applies (so on MGC, in-loss closes are still gated → canal
        break fallback). Documented as a known asymmetry.
        """
        idx = data.index
        fast_l = self._as_bool_array(result["fast_hma_exit_long"])
        fast_s = self._as_bool_array(result["fast_hma_exit_short"])
        trigger = fast_l | fast_s
        self._or_bool_series(result, "hw_cross_over", trigger, idx)
        self._or_bool_series(result, "hw_cross_under", trigger, idx)

    def _apply_exit_hw_only_if_profit(self, result, data, p):
        """H2 — Wait for HW (V3 default) but exit only if in profit.

        Injects partial_close_long/short = hw_cross_under/over (the HW
        events that V3 uses for its exit confirmation). With
        ``tp1_partial_pct = 1.0`` (set in get_simulator_settings), the
        simulator's partial path closes 100% only when in profit; otherwise
        nothing happens and the position keeps running until the next HW
        event or another exit condition.

        Implementation choice: pairing partial_close with hw_cross_*
        events means the partial fires at the same bar as V3 would have
        triggered Canal Exit — minus the in-loss case. The remaining V3
        machinery (fast_hma_exit → pending → HW → Canal Exit) would
        still fire in-loss, so we MUST also neutralise V3's HW-driven
        Canal Exit when this flag is on. We do that by clearing
        hw_cross_over/under for the simulator path, but keeping the
        partial trigger series. After the partial fires 100%, position
        is closed; if not (in loss), no V3 exit fires → wait next HW.
        """
        idx = data.index
        hw_over = self._as_bool_array(result["hw_cross_over"])
        hw_under = self._as_bool_array(result["hw_cross_under"])
        # Partial fires at HW events (in-profit check happens in simulator).
        # Long partial fires on hw_cross_under (the contra HW); short on over.
        self._or_bool_series(result, "partial_close_long", hw_under, idx)
        self._or_bool_series(result, "partial_close_short", hw_over, idx)
        # Disable V3's HW-driven Canal Exit so in-loss HW doesn't close.
        # The fast_hma_exit arming becomes a no-op without an hw_cross to
        # confirm; canal-break fallback still works once loss_exit_blocked
        # would have latched, but that latch needs hw_cross_any to be True
        # which we're disabling — so on MGC (block_loss=True) the trade
        # waits for the next genuine HW event. That's the brief's intent.
        result["hw_cross_over"] = pd.Series(np.zeros_like(hw_over, dtype=bool), index=idx)
        result["hw_cross_under"] = pd.Series(np.zeros_like(hw_under, dtype=bool), index=idx)

    def _apply_exit_on_canal_flip(self, result, data, p):
        """H3 — Close on contra-direction canal HMA flip.

        Fires fast_hma_exit + hw_cross at hma_flip_down (long exit) or
        hma_flip_up (short exit) bars, so V3's full close logic engages.
        Asymmetry caveat: same block_loss gating as H1 applies on MGC.
        """
        idx = data.index
        flip_up = self._as_bool_array(result["hma_flip_up"])
        flip_down = self._as_bool_array(result["hma_flip_down"])
        self._or_bool_series(result, "fast_hma_exit_long", flip_down, idx)
        self._or_bool_series(result, "fast_hma_exit_short", flip_up, idx)
        # OR same-bar HW cross to fire immediately
        self._or_bool_series(result, "hw_cross_over", flip_up | flip_down, idx)
        self._or_bool_series(result, "hw_cross_under", flip_up | flip_down, idx)

    def _apply_exit_mfe_floor(self, result, data, p):
        """H4 — MFE-floor exit.

        Requires intra-trade state. Reconstruct positions from
        long_entries/short_entries; track MFE; fire a partial_close (100%)
        when MFE crossed ``lab_exit_mfe_floor_trigger_r`` and price falls
        back to entry + floor_r × initial_risk. Uses the simulator's
        partial slot with tp1_partial_pct = 1.0.

        Approximation: SL distance for "R" sizing is read from sl_long/sl_short
        at the entry bar. Cooldown / blackouts not modeled — strategy-level
        MFE will over-count when simulator blocks an entry the strategy
        flagged. Documented in REPORT § Limites.
        """
        floor_r = float(p["lab_exit_mfe_floor_r"])
        trigger_r = float(p.get("lab_exit_mfe_floor_trigger_r", floor_r * 2))
        if trigger_r <= floor_r:
            trigger_r = floor_r * 2  # ensure trigger > floor for "give-back" semantics

        idx = data.index
        n = len(data)
        long_entries = self._as_bool_array(result["long_entries"])
        short_entries = self._as_bool_array(result["short_entries"])
        sl_long = result["sl_long"].values
        sl_short = result["sl_short"].values
        close = data["Close"].values
        high = data["High"].values
        low = data["Low"].values

        partial_long = np.zeros(n, dtype=bool)
        partial_short = np.zeros(n, dtype=bool)

        # Track at most one "active" long and one "active" short shadow trade.
        # When the simulator's actual exit might fire earlier, we'll over-trigger
        # but the simulator's in-profit gate will filter false partials.
        active_long_entry = None
        active_long_sl = None
        active_long_mfe = 0.0
        active_short_entry = None
        active_short_sl = None
        active_short_mfe = 0.0

        for i in range(n):
            if long_entries[i] and not np.isnan(sl_long[i]):
                active_long_entry = close[i]
                active_long_sl = sl_long[i]
                active_long_mfe = 0.0
            if short_entries[i] and not np.isnan(sl_short[i]):
                active_short_entry = close[i]
                active_short_sl = sl_short[i]
                active_short_mfe = 0.0

            if active_long_entry is not None and active_long_sl is not None:
                risk = active_long_entry - active_long_sl
                if risk > 0:
                    cur_r = (high[i] - active_long_entry) / risk
                    if cur_r > active_long_mfe:
                        active_long_mfe = cur_r
                    if active_long_mfe >= trigger_r:
                        give_back_lvl = active_long_entry + risk * floor_r
                        if low[i] <= give_back_lvl:
                            partial_long[i] = True
                            active_long_entry = None
                            active_long_sl = None
                            active_long_mfe = 0.0

            if active_short_entry is not None and active_short_sl is not None:
                risk = active_short_sl - active_short_entry
                if risk > 0:
                    cur_r = (active_short_entry - low[i]) / risk
                    if cur_r > active_short_mfe:
                        active_short_mfe = cur_r
                    if active_short_mfe >= trigger_r:
                        give_back_lvl = active_short_entry - risk * floor_r
                        if high[i] >= give_back_lvl:
                            partial_short[i] = True
                            active_short_entry = None
                            active_short_sl = None
                            active_short_mfe = 0.0

        self._or_bool_series(result, "partial_close_long", partial_long, idx)
        self._or_bool_series(result, "partial_close_short", partial_short, idx)

    def _apply_exit_fast_cross_after_bars(self, result, data, p):
        """H5 — Time-based fast-cross-only after N bars.

        After N bars from entry, switch the trigger from "fast cross → HW"
        to "fast cross only". Implementation: OR hw_cross_over/under at
        fast_hma_exit bars only when ``bar_idx - entry_bar >= N``.
        Tracking is shadow-based (same caveat as H4).
        """
        n_bars = int(p["lab_exit_fast_cross_after_bars"])
        idx = data.index
        n = len(data)
        long_entries = self._as_bool_array(result["long_entries"])
        short_entries = self._as_bool_array(result["short_entries"])
        fast_l = self._as_bool_array(result["fast_hma_exit_long"])
        fast_s = self._as_bool_array(result["fast_hma_exit_short"])

        long_entry_bar = -1
        short_entry_bar = -1
        trigger_long = np.zeros(n, dtype=bool)
        trigger_short = np.zeros(n, dtype=bool)

        for i in range(n):
            if long_entries[i]:
                long_entry_bar = i
            if short_entries[i]:
                short_entry_bar = i
            if long_entry_bar >= 0 and (i - long_entry_bar) >= n_bars and fast_l[i]:
                trigger_long[i] = True
                long_entry_bar = -1
            if short_entry_bar >= 0 and (i - short_entry_bar) >= n_bars and fast_s[i]:
                trigger_short[i] = True
                short_entry_bar = -1

        # OR same-bar HW cross so V3 fires immediately at the time-based trigger.
        trigger = trigger_long | trigger_short
        self._or_bool_series(result, "hw_cross_over", trigger, idx)
        self._or_bool_series(result, "hw_cross_under", trigger, idx)

    # ------------------------------------------------------------------ #
    # Levier PT helpers                                                  #
    # ------------------------------------------------------------------ #

    def _apply_pt_on_fast_cross(self, result, data, p):
        """H6 — Partial X% at fast cross (in-profit only, simulator gate)."""
        idx = data.index
        fast_l = self._as_bool_array(result["fast_hma_exit_long"])
        fast_s = self._as_bool_array(result["fast_hma_exit_short"])
        self._or_bool_series(result, "partial_close_long", fast_l, idx)
        self._or_bool_series(result, "partial_close_short", fast_s, idx)

    def _apply_pt_on_canal_flip(self, result, data, p):
        """H7 — Partial X% at canal HMA flip (contra direction)."""
        idx = data.index
        flip_up = self._as_bool_array(result["hma_flip_up"])
        flip_down = self._as_bool_array(result["hma_flip_down"])
        # Long partial fires at flip-down (canal turns red); short at flip-up.
        self._or_bool_series(result, "partial_close_long", flip_down, idx)
        self._or_bool_series(result, "partial_close_short", flip_up, idx)

    def _apply_pt_on_mfe(self, result, data, p):
        """H8 — Partial X% once MFE crosses ``lab_pt_on_mfe_r_trigger`` (R)."""
        trigger_r = float(p["lab_pt_on_mfe_r_trigger"])
        if trigger_r <= 0:
            return  # nothing to do — defensive

        idx = data.index
        n = len(data)
        long_entries = self._as_bool_array(result["long_entries"])
        short_entries = self._as_bool_array(result["short_entries"])
        sl_long = result["sl_long"].values
        sl_short = result["sl_short"].values
        high = data["High"].values
        low = data["Low"].values

        partial_long = np.zeros(n, dtype=bool)
        partial_short = np.zeros(n, dtype=bool)

        active_long_entry = None
        active_long_sl = None
        active_long_taken = False
        active_short_entry = None
        active_short_sl = None
        active_short_taken = False

        for i in range(n):
            if long_entries[i] and not np.isnan(sl_long[i]):
                active_long_entry = data["Close"].values[i]
                active_long_sl = sl_long[i]
                active_long_taken = False
            if short_entries[i] and not np.isnan(sl_short[i]):
                active_short_entry = data["Close"].values[i]
                active_short_sl = sl_short[i]
                active_short_taken = False

            if (active_long_entry is not None and active_long_sl is not None
                    and not active_long_taken):
                risk = active_long_entry - active_long_sl
                if risk > 0:
                    target = active_long_entry + risk * trigger_r
                    if high[i] >= target:
                        partial_long[i] = True
                        active_long_taken = True

            if (active_short_entry is not None and active_short_sl is not None
                    and not active_short_taken):
                risk = active_short_sl - active_short_entry
                if risk > 0:
                    target = active_short_entry - risk * trigger_r
                    if low[i] <= target:
                        partial_short[i] = True
                        active_short_taken = True

        self._or_bool_series(result, "partial_close_long", partial_long, idx)
        self._or_bool_series(result, "partial_close_short", partial_short, idx)
