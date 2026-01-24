<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/react-19.x-61dafb.svg" alt="React">
  <img src="https://img.shields.io/badge/fastapi-0.109+-009688.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/version-1.3--beta-orange.svg" alt="Version">
</p>

# Nebular Apollo - Quantitative Backtesting Engine

A professional-grade backtesting system for trading strategies on CME futures (MNQ, MES, MYM, MGC) and cryptocurrencies, featuring a modern React dashboard and Python-powered analytics engine.

---

## Table of Contents

- [Features](#features)
- [Demo](#demo)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Adding Custom Strategies](#adding-custom-strategies)
- [Supported Assets](#supported-assets)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-source Data** | TopStepX API for futures, Yahoo Finance for crypto/stocks |
| **130+ Indicators** | Full pandas-ta library for technical analysis |
| **Risk Management** | Automatic position sizing based on risk per trade |
| **Fast Backtesting** | VectorBT engine for ultra-fast vectorized simulations |
| **Parameter Optimization** | Grid search to find optimal strategy settings |
| **Session Analysis** | Filter and analyze trades by Asia/UK/US sessions |
| **Modern Dashboard** | React 19 + Tailwind CSS responsive interface |
| **Real-time Metrics** | Win rate, Sharpe ratio, max drawdown, equity curve |
| **Docker Ready** | Multi-stage Dockerfile for easy deployment |

---

## Demo

```
┌─────────────────────────────────────────────────────────────────────┐
│  NEBULAR APOLLO - Quantitative Engine                    v1.3-beta │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐  ┌─────────────────────────────────────────────┐  │
│  │ DATA SOURCE │  │              EQUITY CURVE                   │  │
│  │ ○ Yahoo     │  │    $52,000 ┤                          ╱     │  │
│  │ ● Topstep   │  │            │                       ╱╲╱      │  │
│  ├─────────────┤  │    $50,000 ┼──────────────────╱╲╱╲╱         │  │
│  │ RISK MGMT   │  │            │              ╱╲╱╲              │  │
│  │ Capital: $50K│  │    $48,000 ┤         ╱╲╱╲                   │  │
│  │ Risk: 1%    │  │            └─────────────────────────────── │  │
│  ├─────────────┤  └─────────────────────────────────────────────┘  │
│  │ STRATEGY    │                                                   │
│  │ RobReversal │  ┌──────────┬──────────┬──────────┬──────────┐   │
│  │ EMA: 8      │  │ RETURN   │ WIN RATE │ TRADES   │ DRAWDOWN │   │
│  │ TP: 35 pts  │  │ +4.25%   │ 58.3%    │ 24       │ -2.1%    │   │
│  │ SL: 35 pts  │  └──────────┴──────────┴──────────┴──────────┘   │
│  └─────────────┘                                                   │
│                    [▶ RUN BACKTEST]                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

Before you begin, ensure you have the following installed:

| Requirement | Version | Check command |
|-------------|---------|---------------|
| **Python** | 3.11+ | `python --version` |
| **Node.js** | 20+ | `node --version` |
| **npm** | 10+ | `npm --version` |
| **Git** | 2.x | `git --version` |

### Optional

- **Docker** & **Docker Compose** - For containerized deployment
- **TopStepX Account** - For futures data (free tier available)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/toini666/strat-backtester.git
cd strat-backtester
```

### 2. Backend Setup (Python)

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

> **Note for Apple Silicon (M1/M2)**: NumPy is constrained to <1.24 for numba compatibility. If you encounter issues, try:
> ```bash
> pip install --no-cache-dir numpy==1.23.5
> ```

### 3. Frontend Setup (Node.js)

```bash
cd frontend
npm install
cd ..
```

### 4. Environment Configuration

```bash
# Backend environment
cp .env.example .env

# Frontend environment
cp frontend/.env.example frontend/.env.local
```

Edit `.env` and add your credentials (see [Configuration](#configuration)).

---

## Quick Start

### Option 1: Development Mode (Recommended)

Open **two terminal windows**:

**Terminal 1 - Backend:**
```bash
cd backend
uvicorn main:app --reload --port 8001
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

### Option 2: Docker

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f
```

Access the application at http://localhost:8001

---

## Configuration

### Backend (`.env`)

```bash
# Server Configuration
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
ENV=development                   # development, production

# CORS - Allowed origins (comma-separated)
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# TopStepX API (Optional - for futures data)
TOPSTEP_USERNAME=your_username
TOPSTEPX_TOKEN=your_api_key
```

### Frontend (`frontend/.env.local`)

```bash
# API URL - Backend server address
VITE_API_URL=http://localhost:8001
```

### Getting TopStepX Credentials

1. Create a free account at [TopStepX](https://www.topstepx.com)
2. Navigate to API Settings in your dashboard
3. Generate an API key
4. Copy your username and API key to `.env`

---

## Usage

### Running a Backtest

1. **Select Data Source**: Choose Yahoo Finance or TopStepX
2. **Configure Asset**: Enter ticker (e.g., `BTC-USD`) or select contract
3. **Set Timeframe**: Choose interval (1m, 5m, 15m, 1h, 1d) and period
4. **Configure Risk**: Set initial capital and risk per trade (%)
5. **Select Strategy**: Choose from available strategies
6. **Adjust Parameters**: Fine-tune strategy parameters
7. **Run Backtest**: Click "Run Backtest" and analyze results

### Analyzing Results

- **KPI Cards**: Total return, win rate, trade count, max drawdown
- **Equity Curve**: Visual representation of portfolio growth
- **Trade History**: Detailed log of all trades with P&L
- **Session Analytics**: Performance breakdown by Asia/UK/US sessions
- **Session Filters**: Toggle sessions to see filtered performance

---

## Project Structure

```
strat-backtester/
│
├── backend/                    # FastAPI Backend
│   ├── __init__.py
│   ├── main.py                 # App entry point, CORS, middleware
│   └── api.py                  # API routes and business logic
│
├── src/                        # Core Python Modules
│   ├── data/                   # Data providers
│   │   ├── base.py             # Abstract DataProvider class
│   │   ├── yfinance_provider.py
│   │   ├── topstep.py          # TopStepX API client
│   │   └── csv_provider.py
│   │
│   ├── strategies/             # Trading strategies
│   │   ├── base.py             # Abstract Strategy class
│   │   ├── indicators.py       # pandas-ta wrapper
│   │   ├── signals.py          # StrategySignals dataclass
│   │   ├── rob_reversal.py     # Main strategy
│   │   └── examples/           # Example strategies
│   │
│   ├── engine/                 # Backtesting engine
│   │   └── backtester.py       # VectorBT wrapper
│   │
│   ├── risk/                   # Risk management
│   │   └── position_sizer.py   # Position sizing calculator
│   │
│   ├── optimizer/              # Parameter optimization
│   │   └── grid_search.py      # Grid search optimizer
│   │
│   └── reports/                # Reporting
│       └── visualizer.py       # Plotly charts
│
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── main.tsx            # React entry point
│   │   ├── App.tsx             # Main component
│   │   ├── api.ts              # API client
│   │   └── components/         # UI components
│   │       ├── Layout.tsx
│   │       ├── Sidebar.tsx
│   │       ├── Dashboard.tsx
│   │       ├── KpiCard.tsx
│   │       ├── EquityChart.tsx
│   │       └── TradesTable.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── libs/                       # Local dependencies
│   └── pandas-ta/              # Custom pandas-ta fork
│
├── tests/                      # Test suite
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_strategies.py
│   └── test_data_providers.py
│
├── .env.example                # Environment template
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker build
├── docker-compose.yml          # Docker orchestration
├── pytest.ini                  # Pytest configuration
├── architecture.md             # Technical documentation
└── README.md                   # This file
```

---

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/health` | Detailed health status |
| `GET` | `/strategies` | List available strategies |
| `GET` | `/topstep/contracts` | List TopStepX contracts |
| `POST` | `/backtest` | Execute a backtest |

### POST `/backtest`

**Request Body:**
```json
{
  "strategy_name": "RobReversal",
  "ticker": "BTC-USD",
  "source": "Yahoo",
  "contract_id": null,
  "interval": "15m",
  "days": 14,
  "initial_equity": 50000,
  "risk_per_trade": 0.01,
  "params": {
    "ema_length": 8,
    "take_profit": 35,
    "max_stop_loss": 35
  }
}
```

**Response:**
```json
{
  "metrics": {
    "total_return": 4.25,
    "win_rate": 58.3,
    "total_trades": 24,
    "max_drawdown": -2.1,
    "sharpe_ratio": 1.45
  },
  "trades": [...],
  "equity_curve": [...]
}
```

### Interactive API Docs

When the backend is running, access:
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

---

## Adding Custom Strategies

### Step 1: Create Strategy File

Create `src/strategies/my_strategy.py`:

```python
from .base import Strategy
import pandas as pd
import pandas_ta_classic as ta

class MyStrategy(Strategy):
    """
    My custom trading strategy.

    Long when RSI crosses above 30 (oversold).
    Exit when RSI crosses above 70 (overbought).
    """

    name = "MyStrategy"

    default_params = {
        "rsi_length": 14,
        "oversold": 30,
        "overbought": 70,
        "stop_loss_pct": 0.02
    }

    # Optional: Define ranges for optimization
    param_ranges = {
        "rsi_length": range(10, 20, 2),
        "oversold": [20, 25, 30],
        "overbought": [70, 75, 80]
    }

    def generate_signals(self, data: pd.DataFrame, params: dict = None):
        p = self.get_params(params)

        # Calculate RSI
        rsi = ta.rsi(data['Close'], length=p['rsi_length'])

        # Entry: RSI crosses above oversold level
        entries = (rsi > p['oversold']) & (rsi.shift(1) <= p['oversold'])

        # Exit: RSI crosses above overbought level
        exits = (rsi > p['overbought']) & (rsi.shift(1) <= p['overbought'])

        return entries, exits

    def get_stop_loss(self, data, entry_idx, params=None):
        """Calculate stop loss price."""
        p = self.get_params(params)
        entry_price = data['Close'].iloc[entry_idx]
        return entry_price * (1 - p['stop_loss_pct'])
```

### Step 2: Done!

The strategy is **automatically discovered** on server startup. If running with `--reload`, it will appear immediately in the frontend dropdown.

### Strategy Return Formats

| Format | Return Value | Use Case |
|--------|--------------|----------|
| **Simple** | `(entries, exits)` | Long-only strategies |
| **Long/Short** | `(long_entries, long_exits, short_entries, short_exits)` | Bidirectional |
| **Advanced** | `+ execution_price, sl_distance` | Custom execution/sizing |

---

## Supported Assets

### Futures (via TopStepX)

| Symbol | Name | Tick Size | Tick Value | Fees (RT) |
|--------|------|-----------|------------|-----------|
| MNQ | Micro Nasdaq | 0.25 | $0.50 | $0.74 |
| MES | Micro S&P 500 | 0.25 | $1.25 | $0.74 |
| MYM | Micro Dow | 1.00 | $0.50 | $0.74 |
| MGC | Micro Gold | 0.10 | $1.00 | $1.24 |
| MCL | Micro Crude | 0.01 | $1.00 | $1.04 |
| M6E | Micro EUR/USD | 0.0001 | $1.25 | $0.52 |

### Crypto & Stocks (via Yahoo Finance)

| Symbol | Name |
|--------|------|
| BTC-USD | Bitcoin |
| ETH-USD | Ethereum |
| SPY | S&P 500 ETF |
| QQQ | Nasdaq ETF |
| AAPL | Apple Inc. |
| *Any ticker* | Yahoo Finance supported |

---

## Testing

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=src --cov=backend --cov-report=html
open htmlcov/index.html
```

### Run Specific Tests

```bash
# API tests
pytest tests/test_api.py -v

# Strategy tests
pytest tests/test_strategies.py -v

# Data provider tests
pytest tests/test_data_providers.py -v
```

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures
│   └── sample_ohlcv_data # Sample OHLCV DataFrame
├── test_api.py           # FastAPI endpoint tests
├── test_strategies.py    # Strategy logic tests
└── test_data_providers.py # Data provider tests (mocked)
```

---

## Deployment

### Docker (Recommended)

```bash
# Production build
docker build -t nebular-apollo .

# Run container
docker run -d \
  -p 8001:8001 \
  -e ALLOWED_ORIGINS="https://yourdomain.com" \
  -e LOG_LEVEL=INFO \
  nebular-apollo
```

### Docker Compose

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f backend
```

### Manual Deployment

```bash
# Backend (production)
pip install gunicorn
gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001

# Frontend (build static files)
cd frontend
npm run build
# Serve 'dist/' folder with nginx/apache
```

---

## Troubleshooting

### Common Issues

<details>
<summary><strong>ModuleNotFoundError: No module named 'pandas_ta'</strong></summary>

The project uses a local fork of pandas-ta. Install it with:
```bash
pip install -e ./libs/pandas-ta
```
</details>

<details>
<summary><strong>NumPy/Numba compatibility error on Apple Silicon</strong></summary>

```bash
pip uninstall numpy numba llvmlite
pip install numpy==1.23.5 numba==0.56.4 llvmlite==0.39.1
```
</details>

<details>
<summary><strong>CORS error in browser</strong></summary>

Ensure `ALLOWED_ORIGINS` in `.env` includes your frontend URL:
```bash
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```
</details>

<details>
<summary><strong>TopStepX authentication failed</strong></summary>

1. Verify your credentials in `.env`
2. Check if your API key is still valid
3. Ensure you're using SIM/Combine data (not Live)
</details>

<details>
<summary><strong>Backend not starting</strong></summary>

Check if port 8001 is already in use:
```bash
lsof -i :8001
# Kill the process if needed
kill -9 <PID>
```
</details>

---

## Contributing

Contributions are welcome! Please follow these steps:

### 1. Fork the Repository

```bash
git clone https://github.com/YOUR_USERNAME/strat-backtester.git
```

### 2. Create a Feature Branch

```bash
git checkout -b feature/amazing-feature
```

### 3. Make Your Changes

- Follow the existing code style
- Add tests for new features
- Update documentation if needed

### 4. Run Tests

```bash
pytest
```

### 5. Commit and Push

```bash
git commit -m "Add amazing feature"
git push origin feature/amazing-feature
```

### 6. Open a Pull Request

Go to the repository and click "New Pull Request".

### Code Style

- **Python**: Follow PEP 8, use type hints
- **TypeScript**: Use strict mode, avoid `any`
- **Commits**: Use conventional commits (`feat:`, `fix:`, `docs:`)

---

## Roadmap

### v1.4 (Planned)

- [ ] Walk-forward optimization
- [ ] Monte Carlo simulation
- [ ] Multi-asset portfolio backtesting
- [ ] Trade replay visualization

### v1.5 (Planned)

- [ ] Database persistence (PostgreSQL)
- [ ] User authentication
- [ ] Strategy marketplace
- [ ] Real-time paper trading

### v2.0 (Future)

- [ ] Live trading integration
- [ ] Machine learning strategies
- [ ] Cloud deployment (AWS/GCP)
- [ ] Mobile app

---

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 Nebular Apollo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## Acknowledgments

- **[VectorBT](https://github.com/polakowo/vectorbt)** - High-performance backtesting engine
- **[pandas-ta](https://github.com/twopirllc/pandas-ta)** - Technical analysis library
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern Python web framework
- **[React](https://react.dev/)** - UI library
- **[Tailwind CSS](https://tailwindcss.com/)** - CSS framework
- **[Recharts](https://recharts.org/)** - Charting library
- **[TopStepX](https://www.topstepx.com/)** - Futures data API

---

<p align="center">
  Made with <span style="color: #e25555;">&#9829;</span> by the Nebular Apollo team
</p>

<p align="center">
  <a href="#nebular-apollo---quantitative-backtesting-engine">Back to top</a>
</p>
