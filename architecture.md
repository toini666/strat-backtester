# Architecture Technique - Nebular Apollo Backtesting Engine

## Vue d'ensemble

**Nebular Apollo** est un moteur de backtesting quantitatif pour les stratégies de trading, conçu pour tester des algorithmes sur des données historiques de marchés financiers (futures, crypto, actions).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                               │
│                         Port 5173 (Vite Dev Server)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  App.tsx ─────► Sidebar.tsx      Dashboard.tsx                              │
│                    │                  │                                     │
│                    ▼                  ▼                                     │
│            Configuration        KpiCard.tsx                                 │
│            des paramètres       EquityChart.tsx                             │
│                                 TradesTable.tsx                             │
└───────────────────────────────────────┬─────────────────────────────────────┘
                                        │ HTTP (axios)
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            BACKEND (FastAPI)                                │
│                              Port 8001                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  main.py ──► api.py ──► /strategies    GET   Liste des stratégies          │
│                     ──► /backtest      POST  Exécution backtest             │
│                     ──► /topstep/*     GET   Données Topstep                │
└───────────────────────────────────────┬─────────────────────────────────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           ▼                            ▼                            ▼
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│   DATA PROVIDERS    │   │   STRATEGY ENGINE   │   │   BACKTEST ENGINE   │
│                     │   │                     │   │                     │
│  • YFinance         │   │  • Strategy (ABC)   │   │  • VectorBT         │
│  • Topstep API      │   │  • RobReversal      │   │  • PositionSizer    │
│  • CSV (extensible) │   │  • MACrossover      │   │  • Portfolio        │
└─────────────────────┘   └─────────────────────┘   └─────────────────────┘
```

---

## Stack Technique

### Backend (Python 3.11+)

| Technologie | Version | Rôle |
|-------------|---------|------|
| **FastAPI** | ≥0.109 | Framework API REST asynchrone |
| **Uvicorn** | ≥0.27 | Serveur ASGI |
| **VectorBT** | ≥0.28 | Moteur de backtesting vectorisé |
| **pandas** | ≥2.0 | Manipulation de données |
| **NumPy** | <1.24 | Calculs numériques (contrainte numba) |
| **yfinance** | <1.0 | Données Yahoo Finance |
| **pandas-ta** | Custom | Indicateurs techniques (lib locale) |
| **Pydantic** | ≥2.5 | Validation des données |
| **slowapi** | ≥0.1.9 | Rate limiting |
| **requests** | ≥2.31 | Client HTTP (Topstep) |

### Frontend (Node.js 20+)

| Technologie | Version | Rôle |
|-------------|---------|------|
| **React** | 19.2 | Framework UI |
| **TypeScript** | ~5.9 | Typage statique |
| **Vite** | 7.x | Build tool et dev server |
| **Tailwind CSS** | 4.x | Framework CSS utilitaire |
| **Recharts** | 3.6 | Graphiques (equity curve) |
| **Axios** | 1.13 | Client HTTP |
| **Lucide React** | 0.56 | Icônes |

---

## Structure des fichiers

```
strat-backtester/
├── backend/                    # API FastAPI
│   ├── __init__.py
│   ├── main.py                 # Point d'entrée, CORS, middleware
│   └── api.py                  # Routes et logique métier
│
├── src/                        # Modules Python core
│   ├── data/                   # Fournisseurs de données
│   │   ├── base.py             # DataProvider (ABC)
│   │   ├── yfinance_provider.py
│   │   ├── topstep.py          # Client API Topstep
│   │   └── csv_provider.py
│   │
│   ├── strategies/             # Stratégies de trading
│   │   ├── base.py             # Strategy (ABC)
│   │   ├── indicators.py       # Wrapper pandas-ta
│   │   ├── signals.py          # StrategySignals dataclass
│   │   ├── rob_reversal.py     # Stratégie principale
│   │   └── examples/
│   │       ├── ma_crossover.py
│   │       └── rsi_reversal.py
│   │
│   ├── engine/                 # Moteur de backtest
│   │   └── backtester.py       # Wrapper VectorBT
│   │
│   ├── risk/                   # Gestion du risque
│   │   └── position_sizer.py   # Calcul de taille de position
│   │
│   ├── optimizer/              # Optimisation de paramètres
│   │   └── grid_search.py      # Grid Search
│   │
│   └── reports/                # Rapports
│       └── visualizer.py       # Graphiques Plotly
│
├── frontend/                   # Application React
│   ├── src/
│   │   ├── main.tsx            # Point d'entrée React
│   │   ├── App.tsx             # Composant principal
│   │   ├── api.ts              # Client API
│   │   └── components/
│   │       ├── Layout.tsx      # Layout global
│   │       ├── Sidebar.tsx     # Configuration
│   │       ├── Dashboard.tsx   # Résultats
│   │       ├── KpiCard.tsx     # Métriques
│   │       ├── EquityChart.tsx # Graphique equity
│   │       └── TradesTable.tsx # Historique trades
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── libs/                       # Dépendances locales
│   └── pandas-ta/              # Fork pandas-ta modifié
│
├── tests/                      # Tests unitaires
│   ├── conftest.py             # Fixtures pytest
│   ├── test_api.py
│   ├── test_strategies.py
│   └── test_data_providers.py
│
├── requirements.txt            # Dépendances Python
├── Dockerfile                  # Build Docker
├── docker-compose.yml          # Orchestration
└── pytest.ini                  # Config pytest
```

---

## Architecture Backend

### Point d'entrée (`backend/main.py`)

```python
# Configuration
- CORS (configurable via ALLOWED_ORIGINS)
- Rate Limiting (slowapi)
- Logging structuré
- Health check endpoints
```

### API Routes (`backend/api.py`)

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `GET /` | GET | Health check basique |
| `GET /health` | GET | Health check détaillé |
| `GET /strategies` | GET | Liste des stratégies disponibles |
| `GET /topstep/contracts` | GET | Contrats Topstep disponibles |
| `POST /backtest` | POST | Exécution d'un backtest |

### Modèle de requête Backtest

```python
class BacktestRequest:
    strategy_name: str      # Nom de la stratégie
    ticker: str             # Symbole (ex: "BTC-USD", "MNQ")
    source: str             # "Yahoo" ou "Topstep"
    contract_id: str?       # ID contrat (Topstep)
    interval: str           # "1m", "5m", "15m", "1h", "1d"
    days: int               # Nombre de jours historiques (1-365)
    params: dict            # Paramètres stratégie
    initial_equity: float   # Capital initial (1000-10M)
    risk_per_trade: float   # Risque par trade (0.1%-10%)
```

### Modèle de réponse Backtest

```python
class BacktestResult:
    metrics: {
        total_return: float,      # Rendement total (%)
        win_rate: float,          # Taux de réussite (%)
        total_trades: int,        # Nombre de trades
        max_drawdown: float,      # Drawdown max (%)
        sharpe_ratio: float       # Ratio de Sharpe
    }
    trades: List[Trade]           # Liste des trades
    equity_curve: List[{time, value}]  # Courbe d'equity
```

---

## Système de Stratégies

### Classe abstraite (`src/strategies/base.py`)

```python
class Strategy(ABC):
    name: str                    # Identifiant unique
    default_params: Dict         # Paramètres par défaut
    param_ranges: Dict           # Plages pour optimisation

    @abstractmethod
    def generate_signals(data, params) -> Tuple[entries, exits, ...]

    def get_stop_loss(data, entry_idx, params) -> Optional[float]
    def get_take_profit(data, entry_idx, params) -> Optional[float]
```

### Format des signaux

Les stratégies peuvent retourner différents formats :

| Format | Éléments | Usage |
|--------|----------|-------|
| **Simple (2)** | `(entries, exits)` | Long-only basique |
| **Standard (4)** | `(long_entries, long_exits, short_entries, short_exits)` | Long/Short |
| **Complet (6)** | `+ execution_price, sl_distance` | Avec sizing dynamique |

### Stratégie RobReversal

Stratégie de reversal sur 15 minutes basée sur :
1. **Contexte** : Direction de la bougie précédente (Bar A)
2. **Sweep** : La bougie actuelle (Bar B) dépasse le high/low de Bar A
3. **Close interne** : Bar B clôture dans le corps de Bar A
4. **Filtre EMA** : Prix vs EMA 8

```python
default_params = {
    "ema_length": 8,
    "take_profit": 35.0,    # Points
    "max_stop_loss": 35.0,  # Points
    "trigger_bars": 1,
    "tick_size": 0.25,
    "block_new_signals": True
}
```

---

## Flux de données

### 1. Chargement des données

```
┌─────────────┐     ┌────────────────┐     ┌─────────────┐
│   Request   │────►│ Data Provider  │────►│  DataFrame  │
│   (ticker,  │     │                │     │   OHLCV     │
│   interval) │     │ • YFinance     │     │             │
└─────────────┘     │ • Topstep      │     └─────────────┘
                    └────────────────┘
```

### 2. Génération des signaux

```
┌─────────────┐     ┌────────────────┐     ┌─────────────────┐
│  DataFrame  │────►│   Strategy     │────►│     Signals     │
│    OHLCV    │     │                │     │                 │
│             │     │ • Indicators   │     │ long_entries    │
└─────────────┘     │ • Logic        │     │ long_exits      │
                    └────────────────┘     │ short_entries   │
                                           │ short_exits     │
                                           │ exec_price      │
                                           │ sl_distance     │
                                           └─────────────────┘
```

### 3. Backtesting

```
┌─────────────────┐     ┌────────────────┐     ┌─────────────────┐
│     Signals     │────►│   VectorBT     │────►│   Portfolio     │
│                 │     │                │     │                 │
│                 │     │ • from_signals │     │ • trades        │
└─────────────────┘     │ • size_type    │     │ • equity        │
                        │ • fees         │     │ • metrics       │
        ┌──────────────►│                │     └─────────────────┘
        │               └────────────────┘
┌───────┴───────┐
│ PositionSizer │
│               │
│ Size = Risk / │
│ (SL * TickVal)│
└───────────────┘
```

---

## Calcul de Position Sizing

### Formule

```
Risk Amount = Capital × Risk Per Trade
SL Ticks    = SL Distance / Tick Size
Position    = Risk Amount / (SL Ticks × Tick Value)
```

### Exemple MNQ (Micro Nasdaq)

```
Capital:      $50,000
Risk:         1% = $500
SL Distance:  35 points
Tick Size:    0.25
Tick Value:   $0.50

SL Ticks = 35 / 0.25 = 140 ticks
Position = $500 / (140 × $0.50) = 7.14 → 7 contrats
```

---

## Spécifications des contrats

### Futures (hardcodés dans `backend/api.py`)

| Symbole | Tick Size | Tick Value | Frais RT |
|---------|-----------|------------|----------|
| ES | 0.25 | $12.50 | $2.80 |
| MES | 0.25 | $1.25 | $0.74 |
| NQ | 0.25 | $5.00 | $2.80 |
| MNQ | 0.25 | $0.50 | $0.74 |
| GC | 0.10 | $10.00 | $3.24 |
| MGC | 0.10 | $1.00 | $1.24 |
| CL | 0.01 | $10.00 | $3.04 |

---

## Sessions de Trading

Le système catégorise les trades par session :

| Session | Heures (UTC) | Code couleur |
|---------|--------------|--------------|
| **Asia** | 00:00 - 08:59 | Jaune |
| **UK** | 09:00 - 15:29 | Bleu |
| **US** | 15:30 - 22:00 | Violet |
| **Outside** | 22:01 - 23:59 | Gris |

---

## Architecture Frontend

### Composants React

```
App.tsx
├── Layout.tsx              # Container principal
├── Sidebar.tsx             # Configuration
│   ├── Data Source         # Yahoo/Topstep
│   ├── Risk Management     # Capital, Risk %
│   └── Strategy Params     # Paramètres dynamiques
└── Dashboard.tsx           # Résultats
    ├── Session Filters     # Filtres Asia/UK/US
    ├── KpiCard.tsx (×4)    # Métriques clés
    ├── EquityChart.tsx     # Graphique Recharts
    └── TradesTable.tsx     # Historique
```

### État de l'application (`App.tsx`)

```typescript
// Configuration
dataSource: 'Yahoo' | 'Topstep'
ticker: string
interval: string
days: number

// Risk
initialEquity: number
riskPerTrade: number

// Strategy
selectedStrategy: Strategy
params: StrategyParams

// Results
result: BacktestResult
filteredResult: BacktestResult  // Filtré par session
selectedSessions: string[]
```

### Client API (`api.ts`)

```typescript
const apiClient = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8001',
    timeout: 120000,  // 2 minutes (backtests longs)
});

// Intercepteur d'erreurs global
apiClient.interceptors.response.use(
    (response) => response,
    (error) => { /* gestion erreurs */ }
);
```

---

## Configuration

### Variables d'environnement Backend

```bash
# .env
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
LOG_LEVEL=INFO
ENV=development

# Topstep (optionnel)
TOPSTEP_USERNAME=your_username
TOPSTEPX_TOKEN=your_api_key
```

### Variables d'environnement Frontend

```bash
# frontend/.env.local
VITE_API_URL=http://localhost:8001
```

---

## Déploiement

### Docker

```bash
# Build et lancement
docker-compose up -d

# Ou build manuel
docker build -t nebular-apollo .
docker run -p 8001:8001 nebular-apollo
```

### Dockerfile (Multi-stage)

1. **Stage 1** : Build backend Python
2. **Stage 2** : Build frontend React
3. **Stage 3** : Image production minimale

### Commandes de développement

```bash
# Backend
cd backend
uvicorn main:app --reload --port 8001

# Frontend
cd frontend
npm install
npm run dev

# Tests
pytest -v
```

---

## Tests

### Structure des tests

```
tests/
├── conftest.py           # Fixtures partagées
│   └── sample_ohlcv_data # DataFrame OHLCV de test
├── test_api.py           # Tests endpoints FastAPI
├── test_strategies.py    # Tests stratégies
└── test_data_providers.py # Tests data providers (mock)
```

### Lancement

```bash
# Tous les tests
pytest

# Avec coverage
pytest --cov=src --cov=backend

# Tests spécifiques
pytest tests/test_strategies.py -v
```

---

## Extensibilité

### Ajouter une nouvelle stratégie

1. Créer `src/strategies/ma_nouvelle_strategie.py`
2. Hériter de `Strategy`
3. Implémenter `generate_signals()`
4. La stratégie est auto-découverte au démarrage

```python
from .base import Strategy

class MaNouvelleStrategie(Strategy):
    name = "MaNouvelleStrategie"
    default_params = {"param1": 10}

    def generate_signals(self, data, params=None):
        p = self.get_params(params)
        # ... logique
        return entries, exits
```

### Ajouter un nouveau data provider

1. Créer `src/data/nouveau_provider.py`
2. Hériter de `DataProvider`
3. Implémenter `fetch()`

```python
from .base import DataProvider

class NouveauProvider(DataProvider):
    def fetch(self, symbol, start, end, timeframe):
        # ... fetch data
        return df  # DataFrame avec Open, High, Low, Close, Volume
```

---

## Limitations connues

1. **VectorBT same-bar entry/exit** : Comportement non déterministe si entrée et sortie sur la même bougie
2. **Position sizing fixe** : Utilise le capital initial (pas de compounding)
3. **Fees approximatifs** : Les frais sont déduits au close du trade, pas en temps réel
4. **Sessions UTC only** : Pas de gestion des fuseaux horaires
5. **Pas de persistence** : Les résultats ne sont pas sauvegardés

---

## Performance

- **Backtests** : ~1-5 secondes pour 14 jours de données 15min
- **Optimisation Grid Search** : Dépend du nombre de combinaisons
- **Memory** : ~200-500 MB pour un backtest standard

---

## Sécurité

- CORS configuré via variables d'environnement
- Rate limiting sur les endpoints
- Validation Pydantic des inputs
- Pas de secrets dans le code (env vars)
- Timeouts sur les requêtes HTTP externes

---

## Maintenance

### Logs

```bash
# Backend logs
LOG_LEVEL=DEBUG uvicorn backend.main:app

# Format des logs
2024-01-15 10:30:00 - backend.api - INFO - Registered strategy: RobReversal
```

### Healthchecks

```bash
# Basic
curl http://localhost:8001/

# Detailed
curl http://localhost:8001/health
```

---

*Document généré automatiquement - Nebular Apollo v1.3-beta*
