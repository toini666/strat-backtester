"""HMA-SSL-Osci v3 — Lab v1.

Bench d'évolutions empiriques de :class:`HMASSLOsciV3`.

Tous les paramètres ajoutés ici ont un default qui reproduit exactement le
comportement V3 — la stratégie Lab sans aucun flag activé == V3 strict
(vérifié par ``00_sanity_lab_equals_v3.py``).

Chaque hypothèse vit dans son propre bloc ``if p.get("<flag>"): …`` et
correspond à un helper privé ``_apply_<name>()`` — indépendante,
désactivable, et supprimable si rejetée.

Campagne : ``scripts/goals/2026-05-17_HMASSLOsciV3_evolution/``
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from .hma_ssl_osci_v3 import HMASSLOsciV3


class HMASSLOsciV3Labv1(HMASSLOsciV3):
    """V3 + flags expérimentaux. Defaults strictement V3."""

    name = "HMASSLOsciV3Labv1"

    default_params = {
        **HMASSLOsciV3.default_params,
        # =====================================================================
        # PILIER A — Conditions d'entrée
        # =====================================================================
        # H-A1 : N'entrer qu'à partir du N-ème bar après le slow-cross (V3=0).
        "lab_entry_min_bars": 0,
        # H-A2 : Ne pas autoriser une entrée sur le bar même du slow-cross.
        # (équivalent strict de "lab_entry_min_bars >= 1", mais binaire pour
        # tester sa contribution isolée des bars suivants)
        # >>> intégré dans H-A1 — pas de paramètre séparé.
        # H-A3 : Filtre SL-distance — refuser entrées si SL est < N points
        # (le trade a peu de marge → SL toxique) ou > M points (range trop large).
        # 0 = inactif (= V3).
        "lab_min_sl_points": 0.0,
        # H-A4 : Filtre bornes des heures d'entrée — refuser entrées dans des
        # heures spécifiques (en plus des blackouts engine). Liste d'heures
        # (référentiel Brussels reference). [] = inactif.
        "lab_entry_blocked_hours": (),
        # =====================================================================
        # PILIER B — Évitement des SL (filtres ex-ante + exits pré-calculés)
        # =====================================================================
        # H-B1 : Filtre candle-aggressivité plus fin que max_candle_pct. Refuse
        # les entrées dont la candle d'entrée a un body > X% de la prev_close,
        # OU dont les 2 dernières candles cumulent un body > Y% (signe d'un
        # mouvement déjà consommé). 0 = inactif.
        "lab_max_2bar_body_pct": 0.0,
        # H-B2 : Exit défensif pré-calculé. Si N bars après l'entrée potentielle,
        # le HW n'a toujours pas crossé en faveur du trade (long: pas de
        # hw_cross_over depuis l'entrée), on demande au simulateur de partial-close
        # via ``partial_close_long/short`` (déjà consommé par le sim quand
        # ``hw_partial_pct`` actif). Mais pour éviter de mixer avec hw_partial_pct,
        # on injecte sur ``partial_close_long/short`` une condition stricte
        # qui force le close (peu importe partial_pct, le sim coupe).
        # IMPORTANT : cette hypothèse nécessite de simuler ex-ante, sans le sim,
        # quel serait le bar d'entrée (= long_entries[i]==True). On lance le
        # "trade virtuel" depuis chaque entrée signalée et on émet le
        # partial_close au bar i+N si la condition tient.
        # 0 = inactif (= V3).
        "lab_no_hw_flip_kill_bars": 0,
        # =====================================================================
        # PILIER C — Optimisation des TP
        # =====================================================================
        # H-C1 : Désactiver l'exit "Canal Exit" (canal_lower/upper consumption
        # par le simulator) sur les bars dont l'heure ≥ X (typiquement 20 ou 21),
        # pour laisser l'auto-close 22:00 prendre le trade in-profit.
        # 0 = inactif (= V3).
        "lab_disable_canal_exit_from_hour": 0,
        # H-C2 : Disable canal exit late ONLY if currently in-profit at the
        # late bar. Plus conservatif que C1. Pour le moment encodé comme un
        # second mode du même paramètre (0 = inactif, autre val = heure à partir
        # de laquelle on cancel canal-exit côté du trade ssi prix favorable).
        # Implémentation via signal `canal_exit_requires_arming` est trop globale;
        # à la place on neutralise canal_lower/upper sur ces bars uniquement
        # quand profitable. Cf. _apply_late_canal_exit_skip().
        # Pas un paramètre séparé — partage la même implémentation que C1
        # avec un sous-flag.
        "lab_disable_canal_exit_late_profit_only": False,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # Param sweep ranges — used by /optimize, helpful as inline doc here too.
    # ─────────────────────────────────────────────────────────────────────────
    param_ranges = {
        **HMASSLOsciV3.param_ranges,
        "lab_entry_min_bars": [0, 1, 2, 3, 4, 5],
        "lab_min_sl_points": [0.0, 5.0, 10.0, 15.0, 20.0, 30.0],
        "lab_max_2bar_body_pct": [0.0, 0.5, 0.7, 1.0, 1.5, 2.0],
        "lab_no_hw_flip_kill_bars": [0, 3, 4, 5, 6, 8],
        "lab_disable_canal_exit_from_hour": [0, 18, 19, 20, 21],
    }

    # ─────────────────────────────────────────────────────────────────────────

    def generate_signals(
        self, data: pd.DataFrame, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        p = self.get_params(params)
        result = super().generate_signals(data, p)

        # === H-A1 — lab_entry_min_bars ──────────────────────────────────────
        min_bars = int(p.get("lab_entry_min_bars", 0))
        if min_bars > 0:
            self._apply_entry_min_bars(result, data, min_bars)

        # === H-A3 — lab_min_sl_points ───────────────────────────────────────
        min_sl = float(p.get("lab_min_sl_points", 0.0))
        if min_sl > 0.0:
            self._apply_min_sl_points(result, data, min_sl)

        # === H-A4 — lab_entry_blocked_hours ─────────────────────────────────
        blocked_hours = tuple(p.get("lab_entry_blocked_hours", ()) or ())
        if blocked_hours:
            self._apply_entry_blocked_hours(result, data, blocked_hours)

        # === H-B1 — lab_max_2bar_body_pct ───────────────────────────────────
        max_2body = float(p.get("lab_max_2bar_body_pct", 0.0))
        if max_2body > 0.0:
            self._apply_max_2bar_body_pct(result, data, max_2body)

        # === H-B2 — lab_no_hw_flip_kill_bars ────────────────────────────────
        kill_bars = int(p.get("lab_no_hw_flip_kill_bars", 0))
        if kill_bars > 0:
            self._apply_no_hw_flip_kill(result, data, kill_bars)

        # === H-C1 — lab_disable_canal_exit_from_hour ────────────────────────
        canal_hour = int(p.get("lab_disable_canal_exit_from_hour", 0))
        if canal_hour > 0:
            late_profit_only = bool(
                p.get("lab_disable_canal_exit_late_profit_only", False)
            )
            self._apply_disable_canal_exit_late(
                result, data, canal_hour, late_profit_only
            )

        return result

    # =========================================================================
    # Helpers privés — un par hypothèse.
    # =========================================================================

    # --- H-A1 -----------------------------------------------------------------
    def _apply_entry_min_bars(
        self, result: Dict[str, Any], data: pd.DataFrame, min_bars: int
    ) -> None:
        """Refuse entries occurring < min_bars after the latest slow-cross setup."""
        setup_long = result["setup_bar_long"].values
        setup_short = result["setup_bar_short"].values
        long_e = result["long_entries"].values.copy()
        short_e = result["short_entries"].values.copy()
        n = len(long_e)
        for i in range(n):
            if long_e[i] and setup_long[i] >= 0:
                if (i - int(setup_long[i])) < min_bars:
                    long_e[i] = False
            if short_e[i] and setup_short[i] >= 0:
                if (i - int(setup_short[i])) < min_bars:
                    short_e[i] = False
        result["long_entries"] = pd.Series(long_e, index=data.index)
        result["short_entries"] = pd.Series(short_e, index=data.index)

    # --- H-A3 -----------------------------------------------------------------
    def _apply_min_sl_points(
        self, result: Dict[str, Any], data: pd.DataFrame, min_sl_points: float
    ) -> None:
        """Refuse entries whose SL distance (close − sl) is < min_sl_points."""
        close = data["Close"].values
        sl_long = result["sl_long"].values
        sl_short = result["sl_short"].values
        long_e = result["long_entries"].values.copy()
        short_e = result["short_entries"].values.copy()
        n = len(long_e)
        for i in range(n):
            if long_e[i] and not np.isnan(sl_long[i]):
                if (close[i] - sl_long[i]) < min_sl_points:
                    long_e[i] = False
            if short_e[i] and not np.isnan(sl_short[i]):
                if (sl_short[i] - close[i]) < min_sl_points:
                    short_e[i] = False
        result["long_entries"] = pd.Series(long_e, index=data.index)
        result["short_entries"] = pd.Series(short_e, index=data.index)

    # --- H-A4 -----------------------------------------------------------------
    def _apply_entry_blocked_hours(
        self, result: Dict[str, Any], data: pd.DataFrame, blocked_hours: tuple
    ) -> None:
        """Refuse entries whose bar hour is in `blocked_hours` (reference Brussels)."""
        from src.engine.simulator import _to_ref_minutes

        long_e = result["long_entries"].values.copy()
        short_e = result["short_entries"].values.copy()
        idx = data.index
        n = len(long_e)
        blocked = set(int(h) for h in blocked_hours)
        for i in range(n):
            if not (long_e[i] or short_e[i]):
                continue
            ts = idx[i]
            ref_min = _to_ref_minutes(ts)
            hour = (ref_min // 60) % 24
            if hour in blocked:
                long_e[i] = False
                short_e[i] = False
        result["long_entries"] = pd.Series(long_e, index=data.index)
        result["short_entries"] = pd.Series(short_e, index=data.index)

    # --- H-B1 -----------------------------------------------------------------
    def _apply_max_2bar_body_pct(
        self, result: Dict[str, Any], data: pd.DataFrame, max_2body: float
    ) -> None:
        """Refuse entries where the cumulative body of the 2 last bars exceeds max_2body% of close."""
        close = data["Close"].values
        open_ = data["Open"].values
        long_e = result["long_entries"].values.copy()
        short_e = result["short_entries"].values.copy()
        n = len(long_e)
        for i in range(1, n):
            if not (long_e[i] or short_e[i]):
                continue
            c = close[i]
            if c == 0 or np.isnan(c):
                continue
            body0 = abs(close[i] - open_[i])
            body1 = abs(close[i - 1] - open_[i - 1]) if i > 0 else 0.0
            cum_body_pct = (body0 + body1) / c * 100.0
            if cum_body_pct > max_2body:
                long_e[i] = False
                short_e[i] = False
        result["long_entries"] = pd.Series(long_e, index=data.index)
        result["short_entries"] = pd.Series(short_e, index=data.index)

    # --- H-B2 -----------------------------------------------------------------
    def _apply_no_hw_flip_kill(
        self, result: Dict[str, Any], data: pd.DataFrame, kill_bars: int
    ) -> None:
        """Defensive exit: arm a fast-HMA exit at the bar where an ADVERSE HW
        cross fires within `kill_bars` bars of a potential entry.

        Rationale (obs-B1b): SL trades have median ``shadow_hw_bars=2`` (bars
        from entry to next adverse HW cross), Canal Exit trades have median
        3–4. An early adverse-HW within 2-5 bars is a strong loser-signature.

        Mechanism: at bar i, scan [i+1 .. i+kill_bars] for adverse HW
        (``hw_cross_under`` for longs, ``hw_cross_over`` for shorts). Inject
        ``fast_hma_exit_long/short`` at the first matching bar. The simulator's
        v3_fast_hma_ssl exit mode arms ``pending_final_exit``; the position
        then closes on the next HW cross.
        """
        hw_over = result["hw_cross_over"].values   # bullish HW flip (adverse for shorts)
        hw_under = result["hw_cross_under"].values  # bearish HW flip (adverse for longs)
        long_e = result["long_entries"].values
        short_e = result["short_entries"].values
        n = len(long_e)

        kill_long = np.zeros(n, dtype=bool)
        kill_short = np.zeros(n, dtype=bool)

        for i in range(n):
            if long_e[i]:
                end = min(i + kill_bars + 1, n)
                # Look for the FIRST adverse HW in [i+1 .. i+kill_bars]
                for j in range(i + 1, end):
                    if hw_under[j]:
                        kill_long[j] = True
                        break
            if short_e[i]:
                end = min(i + kill_bars + 1, n)
                for j in range(i + 1, end):
                    if hw_over[j]:
                        kill_short[j] = True
                        break

        # OR-merge with existing fast_hma_exit series from V3.
        existing_long = result.get("fast_hma_exit_long")
        existing_short = result.get("fast_hma_exit_short")
        if existing_long is not None:
            kill_long = kill_long | existing_long.values
        if existing_short is not None:
            kill_short = kill_short | existing_short.values
        result["fast_hma_exit_long"] = pd.Series(kill_long, index=data.index)
        result["fast_hma_exit_short"] = pd.Series(kill_short, index=data.index)

    # --- H-C1 -----------------------------------------------------------------
    def _apply_disable_canal_exit_late(
        self,
        result: Dict[str, Any],
        data: pd.DataFrame,
        from_hour: int,
        late_profit_only: bool,
    ) -> None:
        """Suppress V3's own ``fast_hma_exit_long/short`` arming after hour X.

        In ``v3_fast_hma_ssl`` mode, ``Canal Exit`` fires via
        ``pending_final_exit AND hw_cross_any`` — NOT via canal_lower/upper.
        To prevent late Canal Exit, we must prevent the arming itself: zero
        out the strategy's own ``fast_hma_exit_long/short`` for bars whose
        hour ≥ from_hour. The only remaining exits late are SL (unchanged)
        and auto-close at 22:00 — which is exactly the intended effect
        (let auto-close take the in-profit trades at H=18-21 instead of
        cutting on a HW cross).

        Note ``loss_exit_blocked`` fallback uses ``canal_lower/upper`` once
        latched — but that only activates if pending_final_exit was armed
        and could not close (allow_canal_exit=False at the time). We do
        NOT neutralize the canal here, so that path is unaffected.
        """
        from src.engine.simulator import _to_ref_minutes

        fast_long = result["fast_hma_exit_long"].values.copy()
        fast_short = result["fast_hma_exit_short"].values.copy()
        idx = data.index
        n = len(fast_long)
        for i in range(n):
            ts = idx[i]
            ref_min = _to_ref_minutes(ts)
            hour = (ref_min // 60) % 24
            if hour >= from_hour:
                fast_long[i] = False
                fast_short[i] = False
        # ``late_profit_only`` is a placeholder: the simulator doesn't expose
        # per-bar 'in profit' state. We document the option but treat as a
        # no-op variant.
        result["fast_hma_exit_long"] = pd.Series(fast_long, index=data.index)
        result["fast_hma_exit_short"] = pd.Series(fast_short, index=data.index)
