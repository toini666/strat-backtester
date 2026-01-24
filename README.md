# Backtesting System for Trading Strategies

A Python-based backtesting system for trading strategies on CME futures (MNQ, MES, MYM, MGC) and cryptocurrencies.

## Features

- 📊 **Multi-source Data**: TopStepX API for futures, yfinance for crypto
- 📈 **Flexible Strategies**: 130+ technical indicators via pandas-ta
- 💰 **Risk Management**: Automatic position sizing based on risk per trade
- ⚡ **Fast Backtesting**: VectorBT engine for ultra-fast simulations
- 🔧 **Parameter Optimization**: Grid search to find optimal settings
- 📉 **Interactive Reports**: Plotly charts in Jupyter notebooks

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure your TopStepX API token
cp .env.example .env
# Edit .env and add your TOPSTEPX_TOKEN

# Launch the Application
# 1. Start Backend
cd backend
uvicorn api:router --reload --port 8001

# 2. Start Frontend (in a new terminal)
cd frontend
npm run dev
```

## How to Add a New Strategy

1. Create a new Python file in `src/strategies/` (e.g., `my_new_strategy.py`).
2. Create a class that inherits from `Strategy` (see `src/strategies/base.py`).
3. Implement the `generate_signals` method.
4. **Done!** The strategy will automatically appear in the Frontend dropdown. No server restart required if running with `--reload`.

## Project Structure

```
src/
├── data/           # Data providers (TopStepX, yfinance)
├── strategies/     # Strategy base class & examples
├── risk/           # Position sizing
├── engine/         # Backtesting engine (VectorBT)
├── optimizer/      # Parameter optimization
└── reports/        # Visualization
└── reports/        # Visualization
```

## Usage

Navigate to `http://localhost:5173` to use the application.

## Supported Assets

| Symbol | Description | Data Source |
|--------|-------------|-------------|
| MNQ | Micro E-mini Nasdaq-100 | TopStepX |
| MES | Micro E-mini S&P 500 | TopStepX |
| MYM | Micro E-mini Dow Jones | TopStepX |
| MGC | Micro Gold | TopStepX |
| BTC-USD | Bitcoin | yfinance |
| ETH-USD | Ethereum | yfinance |

## License

MIT
