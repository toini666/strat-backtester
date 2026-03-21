<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/react-19.x-61dafb.svg" alt="React">
  <img src="https://img.shields.io/badge/fastapi-0.109+-009688.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
</p>

# Nebular Apollo — Backtesting Engine

Moteur de backtesting événementiel pour stratégies de trading sur futures CME (micro-contrats). Il simule des stratégies issues de PineScript sur données OHLCV 1-minute historiques, avec recomposition multi-timeframes, gestion des sessions DST-aware, et un dashboard React pour visualiser les résultats.

---

## Installation (première fois)

```bash
# 1. Cloner le repo (repo public, aucun mot de passe requis)
git clone https://github.com/toini666/strat-backtester.git nebular-apollo
cd nebular-apollo

# 2. Installer tout (Python, Node, dépendances)
bash install.sh

# 3. Lancer l'application
bash start.sh
```

`install.sh` installe automatiquement Homebrew, Python 3 et Node.js si nécessaire.

## Utilisation quotidienne

```bash
bash start.sh
```

Ouvre automatiquement http://localhost:3001 dans le navigateur.

## Mettre à jour l'application

Quand une nouvelle version est disponible :

```bash
bash update.sh
```

Puis relancer avec `bash start.sh`.

---

## Architecture

```
Frontend (React/Vite :3001) → HTTP → Backend (FastAPI :8001)
                                           │
                      ┌────────────────────┼────────────────────┐
                      ▼                    ▼                    ▼
              Data Layer           Strategy Engine        Backtest Engine
           market_store.py         strategies/*.py        simulator.py
           recompose.py            base.py (ABC)          (Event-driven)
```

**Moteur événementiel** (`src/engine/simulator.py`) : traite chaque bar séquentiellement avec résolution intra-bar à la minute. Gère les sorties partielles (TP1/TP2), le breakeven, l'auto-close, les fenêtres de blackout, et le trailing stop.

**Recomposition timeframe** (`src/data/recompose.py`) : reconstruit les bars 3m/5m/7m/15m depuis la 1m en respectant les frontières de session — reproduit exactement le comportement de TradingView.

---

## Stratégies disponibles

Toutes les stratégies ont un fichier PineScript de référence dans `Pinescripts/`.

| Stratégie | Fichier | PineScript | Warmup |
|-----------|---------|-----------|--------|
| EMABreakOsc | `ema_break_osc.py` | `EMA-Break-Osc.txt` | 250 bars |
| EMA9Scalp | `ema9_scalp.py` | `EMA9-scalp.txt` | 80 bars |
| UTBotAlligatorST | `utbot_alligator_st.py` | `UTBot-Alligator-ST.txt` | 120 bars |

Les stratégies sont **auto-découvertes** au démarrage : tout fichier héritant de `Strategy` dans `src/strategies/` apparaît automatiquement dans le frontend.

---

## Instruments supportés

| Symbole | Nom | Tick Size | Tick Value | Frais RT |
|---------|-----|-----------|------------|----------|
| M2K | Micro Russell 2000 | 0.10 | $0.50 | $0.74 |
| MBT | Micro Bitcoin | 5.00 | $0.50 | $2.34 |
| MCL | Micro Crude Oil | 0.01 | $1.00 | $1.04 |
| MES | Micro S&P 500 | 0.25 | $1.25 | $0.74 |
| MGC | Micro Gold | 0.10 | $1.00 | $1.24 |
| MNQ | Micro Nasdaq | 0.25 | $0.50 | $0.74 |
| MYM | Micro Dow Jones | 1.00 | $0.50 | $0.74 |

---

## Configuration

### `.env`

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `TOPSTEPX_TOKEN` | Token API TopStepX (pour mise à jour des données) |
| `TOPSTEPX_USERNAME` | Nom d'utilisateur TopStepX |
| `ALLOWED_ORIGINS` | Origines CORS autorisées (défaut : `http://localhost:3001`) |
| `LOG_LEVEL` | Niveau de log : `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `DEFAULT_INITIAL_CAPITAL` | Capital initial par défaut (défaut : `50000`) |
| `DEFAULT_RISK_PER_TRADE` | Risque par trade en fraction (défaut : `0.01` = 1%) |

Le token TopStepX est optionnel : l'app fonctionne entièrement en backtest sur les données CSV locales sans credentials.

---

## Données de marché

Les données OHLCV 1-minute sont stockées localement dans `data/market_data/<SYMBOL>/`.

**Mise à jour** (requiert un compte TopStepX) :
```bash
source venv/bin/activate
python scripts/update_market_data.py
```

---

## Position sizing

```
Risk Amount = Capital × Risk Par Trade (ex. 1%)
SL Ticks    = |Entrée - Stop Loss| / Tick Size
Contrats    = floor(Risk Amount / (SL Ticks × Tick Value))
```

Sorties partielles basées sur la taille **initiale** de la position :
- TP1 : `floor(initial × tp1_partial_pct)` contrats
- TP2 : `floor(initial × tp2_partial_pct)` contrats
- Reste : fermé à la sortie finale (EMA cross, auto-close, ou fin de données)

---

## Ajouter une stratégie

1. Créer `src/strategies/ma_strategie.py` héritant de `Strategy`
2. Implémenter `generate_signals()` retournant les clés requises
3. Ajouter le warmup dans `STRATEGY_WARMUP_BARS` dans `backend/api.py`
4. Ajouter le fichier PineScript de référence dans `Pinescripts/`

La stratégie apparaît automatiquement dans le frontend au prochain démarrage.

Voir `CLAUDE.md` pour la documentation complète de l'API `generate_signals()`.

---

## Tests

```bash
source venv/bin/activate
pytest -xvs                           # Tous les tests
pytest tests/test_simulator.py -xvs  # Simulateur
pytest tests/test_api.py -xvs        # API + sessions
pytest tests/test_recompose.py -xvs  # Recomposition
```

---

## Sessions & DST

Les sessions Asia / UK / US sont définies en **heure Brussels de référence** (offset US/Eastern = 6h). Le système détecte automatiquement les périodes de transition DST (~3 semaines en mars, ~1 semaine en oct/nov) et ajuste toutes les fenêtres de blackout, l'auto-close et les labels de session — sans configuration manuelle.

---

## Fichiers clés

| Fichier | Rôle |
|---------|------|
| `backend/api.py` | Endpoints FastAPI, orchestration du backtest |
| `src/engine/simulator.py` | Simulateur événementiel |
| `src/data/recompose.py` | Recomposition des timeframes |
| `src/data/market_store.py` | Lecture/écriture des données locales CSV |
| `src/strategies/base.py` | Classe abstraite Strategy |
| `frontend/src/App.tsx` | Racine React, gestion d'état |
| `frontend/src/components/Sidebar.tsx` | UI de configuration du backtest |
| `frontend/src/components/Dashboard.tsx` | Affichage des résultats |

---

## License

MIT License — Copyright (c) 2024 Nebular Apollo
