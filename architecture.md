# Architecture Technique — Nebular Apollo Backtesting Engine

## Vue d'ensemble

**Nebular Apollo** est un moteur de backtesting quantitatif pour les stratégies de trading sur futures (MNQ, MES, MGC, MBT, etc.). Il utilise des données 1-minute locales, recompose les barres en timeframes supérieurs, et propose deux moteurs d'exécution : VectorBT (vectorisé) et un simulateur événementiel avec résolution intra-barre.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React / Vite)                        │
│                           Port 5173                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  App.tsx ──► Sidebar.tsx          Dashboard.tsx                        │
│                 │                      │                               │
│                 ▼                      ▼                               │
│          Configuration           KpiCard.tsx                           │
│          • Stratégie             EquityChart.tsx                       │
│          • Data source           TradesTable.tsx                       │
│          • Risk mgmt             Session Filters                      │
│          • Blackout windows                                           │
│          • Engine settings    OptimizationConfig.tsx                   │
│                               OptimizationResults.tsx                 │
│                               MarketDataPanel.tsx                     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTP (axios)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI)                               │
│                           Port 8001                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  main.py ──► api.py ──────► /backtest      POST  Backtest              │
│                        ──► /strategies     GET   Liste stratégies      │
│                        ──► /optimize       POST  Optimisation grid     │
│          market_data_routes.py                                         │
│                        ──► /market-data/*  GET   Données locales       │
│                        ──► /available-data GET   Plages disponibles    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          ▼                          ▼                          ▼
┌──────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│   DATA LAYER     │   │   STRATEGY ENGINE    │   │   BACKTEST ENGINES   │
│                  │   │                      │   │                      │
│  market_store.py │   │  base.py (ABC)       │   │  backtester.py       │
│  recompose.py    │   │  ema_break_osc.py    │   │    (VectorBT legacy) │
│  topstep.py      │   │  rob_reversal.py     │   │  simulator.py        │
│  yfinance.py     │   │  delta_div.py        │   │    (Event-driven)    │
│  csv_provider.py │   │  utbot_stc.py        │   │    • Partial TP      │
│                  │   │  utbot_occ.py        │   │    • Intra-bar 1m    │
│                  │   │  bulles_bollinger.py  │   │    • Breakeven       │
│                  │   │  brochettes.py       │   │    • Auto-close      │
│                  │   │  vwap_ema.py         │   │    • Blackout        │
│                  │   │  ema9_retest.py      │   │                      │
└──────────────────┘   └──────────────────────┘   └──────────────────────┘
```

---

## Stack Technique

### Backend (Python 3.9+)

| Technologie | Rôle |
|-------------|------|
| **FastAPI** | Framework API REST asynchrone |
| **Uvicorn** | Serveur ASGI |
| **VectorBT** | Moteur de backtesting vectorisé (legacy) |
| **pandas / NumPy** | Manipulation de données, calculs |
| **pandas-ta** | Indicateurs techniques (lib locale dans `libs/`) |
| **Pydantic** | Validation des données |
| **slowapi** | Rate limiting |

### Frontend (Node.js 20+)

| Technologie | Rôle |
|-------------|------|
| **React 19** | Framework UI |
| **TypeScript** | Typage statique |
| **Vite** | Build tool et dev server |
| **Tailwind CSS** | Framework CSS |
| **Recharts** | Graphiques (equity curve) |
| **Axios** | Client HTTP |

---

## Flux de Données

### 1. Données source → 1-minute bars

Les données 1-minute sont stockées localement dans `data/market_data/` (Parquet/CSV) via `market_store.py`. Le script `scripts/update_market_data.py` permet de les mettre à jour depuis l'API Topstep.

### 2. Recomposition de timeframe (`src/data/recompose.py`)

Les barres en timeframe supérieur (3m, 5m, 7m, 15m, 30m, 1h) sont recomposées à partir des données 1m :
- Les barres se **ré-ancrent à chaque début de session** (détecté par un gap > 30 min dans les données 1m)
- Les barres incomplètes en début de session sont supprimées
- Les barres partielles en fin de session sont conservées
- Ce comportement reproduit exactement TradingView

### 3. Buffer de warmup

Les indicateurs nécessitent un historique avant la date de début du backtest. Le warmup est calculé par stratégie :
```
warmup_bars × minutes_par_bar → minutes de trading nécessaires
→ jours de trading → jours calendaires (ratio 7/5 + 3 jours de marge pour weekends)
```

### 4. Génération de signaux

Chaque stratégie produit un dictionnaire avec :
- `long_entries`, `short_entries` : Series booléennes
- `sl_long`, `sl_short` : Series float (prix du stop)
- `tp1_long`, `tp1_short` : Series float (prix du TP1)
- `ema_main`, `ema_secondary` : Series (pour les sorties du simulateur)
- `debug_frame` (optionnel) : DataFrame avec toutes les valeurs d'indicateurs

### 5. Exécution du backtest

**VectorBT** (stratégies simples) : exécution vectorisée, rapide, sans résolution intra-barre.

**Simulateur** (stratégies complexes) : traitement barre par barre avec zoom 1m quand les niveaux SL et TP sont tous deux dans le range d'une barre.

---

## Gestion DST des Sessions et Blackout

### Problème
Le CME suit l'heure US/Eastern. Pendant les périodes de décalage DST (~3 semaines en mars, ~1 semaine en oct/nov), les heures de marché se décalent de -1h en heure de Bruxelles.

### Solution
Toutes les heures configurées sont en **temps de référence Bruxelles** (= quand Bruxelles-ET = 6h). Le système détecte automatiquement le décalage :
- `diff = 6h` → offset = 0 (standard)
- `diff = 5h` → offset = -1 (décalé, sessions 1h plus tôt)

L'heure réelle de Bruxelles est normalisée au cadre de référence avant toute comparaison. Un backtest traversant un changement d'heure fonctionne sans ajustement manuel.

### Sessions (Temps de Référence Bruxelles)

| Session | Heures référence | Heures décalées (offset=-1) |
|---------|------------------|-----------------------------|
| Asia    | 00:00 – 08:59    | 23:00 – 07:59               |
| UK      | 09:00 – 15:29    | 08:00 – 14:29               |
| US      | 15:30 – fin      | 14:30 – fin                 |

Il n'y a **pas de session "Outside"** — tout est Asia, UK ou US. Les blackout windows gèrent les zones d'exclusion.

---

## Simulateur Événementiel (`src/engine/simulator.py`)

### Configuration (`SimulatorConfig`)

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `tp1_partial_pct` | 0.25 | Fraction de la position fermée au TP1 |
| `tp2_partial_pct` | 0.25 | Fraction fermée au TP2 (EMA cross) |
| `tp1_execution_mode` | `"touch"` | `"touch"` ou `"bar_close_if_touched"` |
| `auto_close_hour` | 22 | Heure auto-close (référence) |
| `auto_close_minute` | 0 | Minute auto-close |
| `cooldown_bars` | 0 | Barres minimum entre fermeture et prochaine entrée |
| `blackout_windows` | [] | Fenêtres d'exclusion d'entrée |

### Cycle de vie d'un trade

```
Entrée → [TP1 partiel → Breakeven activé] → [TP2 partiel sur EMA cross]
       → Sortie finale (EMA cross / Auto-close / Stop Loss / End of Data)
```

### Sizing des sorties partielles

Utilise le nombre de contrats **initial** (pas le restant) :
```
TP1 : floor(taille_initiale × tp1_partial_pct) contrats
TP2 : floor(taille_initiale × tp2_partial_pct) contrats
Final : restant
```
Exemple : 9 contrats avec 25%/25% → 2 au TP1, 2 au TP2, 5 à la fermeture finale.

---

## Spécifications des Contrats

| Symbole | Tick Size | Tick Value | Point Value | Fee RT |
|---------|-----------|------------|-------------|--------|
| MNQ     | 0.25      | $0.50      | $2.00       | $0.74  |
| MES     | 0.25      | $1.25      | $5.00       | $0.74  |
| MGC     | 0.10      | $1.00      | $10.00      | $1.24  |
| MBT     | 5.00      | $1.25      | $0.25       | $1.55  |
| NQ      | 0.25      | $5.00      | $20.00      | $2.80  |
| ES      | 0.25      | $12.50     | $50.00      | $2.80  |

---

## Tests

```bash
pytest -xvs                          # Tous les tests
pytest tests/test_simulator.py       # Tests simulateur
pytest tests/test_api.py             # Tests API + sessions DST
pytest tests/test_recompose.py       # Tests recomposition
```

---

## Conventions importantes

1. **Toutes les heures en timezone Bruxelles** — données stockées en UTC, logique métier en `Europe/Brussels`
2. **Temps de référence** — les heures configurées (blackout, auto-close, sessions) sont en temps de référence (offset=0). Le système ajuste automatiquement pour le DST.
3. **Pas de session "Outside"** — supprimée, tous les trades sont Asia, UK ou US
4. **Le warmup n'est pas du backtest** — les barres de warmup sont chargées avant la date de début et supprimées après le calcul des indicateurs
5. **Auto-découverte des stratégies** — toute sous-classe de `Strategy` dans `src/strategies/` est automatiquement enregistrée
6. **pandas-ta local** — la bibliothèque est dans `libs/pandas-ta/`, pas installée via pip
7. **Correspondance PineScript** — les indicateurs doivent reproduire exactement les calculs TradingView
