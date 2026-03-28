import { useState, useEffect, useCallback, useRef } from 'react';
import {
  api,
  type Strategy,
  type BacktestResult,
  type AvailableDataset,
  type Trade,
  type BacktestMetrics,
  type BacktestEngineSettings,
  DEFAULT_BACKTEST_ENGINE_SETTINGS,
} from './api';

type BacktestContext = { symbol: string; interval: string; start: string; end: string };
import './App.css';

// Components
import { Layout } from './components/Layout';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './components/Dashboard';
// Optimization components preserved for future use:
// import { OptimizationConfig } from './components/OptimizationConfig';
// import { OptimizationResults } from './components/OptimizationResults';
// import { OptimizationHistory } from './components/OptimizationHistory';
import { MarketDataPanel } from './components/MarketDataPanel';
import { FavoritesPage } from './components/FavoritesPage';

// Type for strategy parameters
type StrategyParams = Record<string, number | string | boolean>;

// App modes
type AppMode = 'backtest' | 'optimization' | 'data' | 'favorites';

function App() {
  // Mode state
  const [mode, setMode] = useState<AppMode>('backtest');

  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [params, setParams] = useState<StrategyParams>({});

  // Available data from local store
  const [availableData, setAvailableData] = useState<AvailableDataset[]>([]);

  // Data Config - simplified
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [interval, setInterval] = useState('5m');
  const [startDatetime, setStartDatetime] = useState('');
  const [endDatetime, setEndDatetime] = useState('');

  // Risk Mgmt
  const [initialEquity, setInitialEquity] = useState(50000);
  const [riskPerTrade, setRiskPerTrade] = useState(0.5); // %

  // Trade Filters
  const [maxContracts, setMaxContracts] = useState(50);
  const [engineSettings, setEngineSettings] = useState<BacktestEngineSettings>({
    ...DEFAULT_BACKTEST_ENGINE_SETTINGS,
    blackout_windows: DEFAULT_BACKTEST_ENGINE_SETTINGS.blackout_windows.map((window) => ({ ...window })),
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState('');

  // Previous run comparison — tracks metrics from the last completed run (same context only)
  const [previousMetrics, setPreviousMetrics] = useState<BacktestMetrics | null>(null);
  const currentResultContextRef = useRef<BacktestContext | null>(null);
  const filteredResultRef = useRef<BacktestResult | null>(null);

  // Auto-update mode: when enabled, parameter changes trigger automatic resimulation
  const [autoUpdate, setAutoUpdate] = useState(false);
  const [autoUpdateLoading, setAutoUpdateLoading] = useState(false);
  const autoUpdateTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Filters
  const [selectedSessions, setSelectedSessions] = useState<string[]>(['Asia', 'UK', 'US']);

  // Derived state
  const [filteredResult, setFilteredResult] = useState<BacktestResult | null>(null);

  // Optimization state — preserved for future use when optimization UI is re-enabled

  // Load strategies and available data on mount
  useEffect(() => {
    api.getStrategies().then(data => {
      setStrategies(data);
      if (data.length > 0) selectStrategy(data[0]);
    }).catch((err: unknown) => {
      const message = err instanceof Error ? err.message : String(err);
      setError("Failed to load strategies: " + message);
    });

    api.getAvailableData().then(data => {
      setAvailableData(data);
      if (data.length > 0) {
        setSelectedSymbol(data[0].symbol);
        // Set default timeframe
        if (data[0].timeframes.includes('5m')) {
          setInterval('5m');
        } else if (data[0].timeframes.length > 0) {
          setInterval(data[0].timeframes[data[0].timeframes.length - 1]);
        }
        // Set default end datetime to dataset end
        setEndDatetime(data[0].end_date.slice(0, 16)); // trim to YYYY-MM-DDTHH:mm
      }
    }).catch((err: unknown) => {
      const message = err instanceof Error ? err.message : String(err);
      setError("Failed to load available data: " + message);
    });
  }, []);

  // When symbol or strategy changes, set default start datetime considering buffer
  useEffect(() => {
    if (!selectedSymbol || !selectedStrategy || availableData.length === 0) return;
    const ds = availableData.find(d => d.symbol === selectedSymbol);
    if (!ds) return;

    const minStarts = ds.min_start_per_strategy[selectedStrategy.name];
    if (minStarts && minStarts[interval]) {
      const minStart = minStarts[interval];
      // Only update if current startDatetime is before minStart or empty
      if (!startDatetime || startDatetime < minStart.slice(0, 16)) {
        setStartDatetime(minStart.slice(0, 16));
      }
    }
  }, [selectedSymbol, selectedStrategy, interval, availableData]);

  const selectStrategy = useCallback((strat: Strategy) => {
    setSelectedStrategy(strat);
    setParams({ ...strat.default_params });
  }, []);

  const runBacktest = async () => {
    if (!selectedStrategy || !selectedSymbol) return;

    const newContext: BacktestContext = { symbol: selectedSymbol, interval, start: startDatetime, end: endDatetime };

    // Promote current filtered metrics to "previous" if context matches
    const ctx = currentResultContextRef.current;
    const fr = filteredResultRef.current;
    if (fr && ctx && ctx.symbol === newContext.symbol && ctx.interval === newContext.interval &&
        ctx.start === newContext.start && ctx.end === newContext.end) {
      setPreviousMetrics({ ...fr.metrics });
    } else {
      setPreviousMetrics(null);
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const res = await api.runBacktest(
        selectedStrategy.name,
        selectedSymbol,
        interval,
        startDatetime,
        endDatetime,
        initialEquity,
        riskPerTrade / 100, // Send as decimal
        params,
        maxContracts,
        engineSettings,
      );
      setResult(res);
      currentResultContextRef.current = newContext;
      // Track which strategy params were used for signal generation
      lastSignalParamsRef.current = JSON.stringify(params);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  // Keep filteredResultRef in sync so async handlers can read the latest value
  useEffect(() => {
    filteredResultRef.current = filteredResult;
  }, [filteredResult]);

  // Clear previous metrics when the backtest context changes (ticker, timeframe, or date range)
  useEffect(() => {
    const ctx = currentResultContextRef.current;
    if (!ctx) return;
    if (selectedSymbol !== ctx.symbol || interval !== ctx.interval ||
        startDatetime !== ctx.start || endDatetime !== ctx.end) {
      setPreviousMetrics(null);
      currentResultContextRef.current = null;
    }
  }, [selectedSymbol, interval, startDatetime, endDatetime]);

  // Auto-update: debounced re-run when parameters change.
  // - Strategy params change → full backtest (re-generates signals)
  // - Risk/engine params change → fast resimulate (reuses cached signals)
  const autoUpdateRef = useRef({
    initialEquity, riskPerTrade, maxContracts, params, engineSettings,
    selectedStrategy, selectedSymbol, interval, startDatetime, endDatetime,
  });
  autoUpdateRef.current = {
    initialEquity, riskPerTrade, maxContracts, params, engineSettings,
    selectedStrategy, selectedSymbol, interval, startDatetime, endDatetime,
  };
  // Track the last params that were used for signal generation
  const lastSignalParamsRef = useRef<string | null>(null);

  useEffect(() => {
    if (!autoUpdate || !result) return;
    if (autoUpdateTimer.current) clearTimeout(autoUpdateTimer.current);
    autoUpdateTimer.current = setTimeout(async () => {
      const p = autoUpdateRef.current;
      if (!p.selectedStrategy || !p.selectedSymbol) return;

      const newContext: BacktestContext = { symbol: p.selectedSymbol, interval: p.interval, start: p.startDatetime, end: p.endDatetime };

      // Promote current filtered metrics to "previous" if context matches
      const ctx = currentResultContextRef.current;
      const fr = filteredResultRef.current;
      if (fr && ctx && ctx.symbol === newContext.symbol && ctx.interval === newContext.interval &&
          ctx.start === newContext.start && ctx.end === newContext.end) {
        setPreviousMetrics({ ...fr.metrics });
      } else {
        setPreviousMetrics(null);
      }

      // Determine if strategy params changed (need full backtest)
      const currentParamsKey = JSON.stringify(p.params);
      const needsFullBacktest = lastSignalParamsRef.current !== null
        && lastSignalParamsRef.current !== currentParamsKey;

      setAutoUpdateLoading(true);
      try {
        let res: BacktestResult;
        if (needsFullBacktest) {
          // Strategy params changed → full backtest to regenerate signals
          res = await api.runBacktest(
            p.selectedStrategy.name,
            p.selectedSymbol,
            p.interval,
            p.startDatetime,
            p.endDatetime,
            p.initialEquity,
            p.riskPerTrade / 100,
            p.params,
            p.maxContracts,
            p.engineSettings,
          );
          lastSignalParamsRef.current = currentParamsKey;
        } else {
          // Only risk/engine changed → fast resimulate with cached signals
          res = await api.resimulate(
            p.initialEquity,
            p.riskPerTrade / 100,
            p.maxContracts,
            p.params,
            p.engineSettings,
          );
        }
        setResult(res);
        currentResultContextRef.current = newContext;
        setError('');
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        setError(message);
      } finally {
        setAutoUpdateLoading(false);
      }
    }, 400);
    return () => {
      if (autoUpdateTimer.current) clearTimeout(autoUpdateTimer.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoUpdate, initialEquity, riskPerTrade, maxContracts, params, engineSettings]);

  // Helper to calc metrics on a subset of trades
  const calculateMetrics = useCallback((trades: Trade[], equity: number): BacktestMetrics => {
    let currentEquity = equity;
    let peak = equity;
    let maxDrawdown = 0;

    let cumPnL = 0;
    let winCount = 0;

    trades.forEach(t => {
      cumPnL += t.pnl;
      currentEquity += t.pnl;
      if (currentEquity > peak) peak = currentEquity;
      const dd = (peak - currentEquity) / peak;
      if (dd > maxDrawdown) maxDrawdown = dd;
      if (t.pnl > 0) winCount++;
    });

    return {
      total_return: (cumPnL / equity) * 100,
      win_rate: trades.length > 0 ? (winCount / trades.length) * 100 : 0,
      total_trades: trades.length,
      max_drawdown: maxDrawdown * 100,
      sharpe_ratio: 0
    };
  }, []);

  useEffect(() => {
    if (!result) {
      setFilteredResult(null);
      return;
    }

    const filteredTrades = result.trades.filter(t => selectedSessions.includes(t.session));
    const activeTrades = filteredTrades.filter(t => !t.excluded);
    const newMetrics = calculateMetrics(activeTrades, initialEquity);

    let currentEq = initialEquity;
    const newCurve = [{ time: 'Start', value: initialEquity }];
    activeTrades.forEach((t, i) => {
      currentEq += t.pnl;
      newCurve.push({ time: t.exit_execution_time || t.exit_time || String(i), value: currentEq });
    });

    setFilteredResult({
      metrics: { ...result.metrics, ...newMetrics },
      trades: filteredTrades,
      equity_curve: newCurve,
      daily_limits_hit: result.daily_limits_hit,
      data_source_used: result.data_source_used,
      debug_file: result.debug_file,
    });

  }, [result, selectedSessions, initialEquity, calculateMetrics]);


  // Optimization handlers — preserved as comments for future use when optimization UI is re-enabled

  const handleLoadFavoritePreset = useCallback((preset: import('./api').BacktestPreset) => {
    const strat = strategies.find(s => s.name === preset.strategyName);
    if (strat) {
      selectStrategy(strat);
      setTimeout(() => setParams({ ...strat.default_params, ...preset.params }), 0);
    }
    setSelectedSymbol(preset.symbol);
    setInterval(preset.interval);
    setStartDatetime(preset.startDatetime);
    setEndDatetime(preset.endDatetime);
    setInitialEquity(preset.initialEquity);
    setRiskPerTrade(preset.riskPerTrade);
    setMaxContracts(preset.maxContracts);
    setEngineSettings(JSON.parse(JSON.stringify(preset.engineSettings)));
    setMode('backtest');
  }, [strategies, selectStrategy]);

  return (
    <Layout>
      {/* Mode Toggle */}
      <div className="mb-6 flex items-center gap-4">
        <div className="inline-flex rounded-lg bg-gray-800/50 p-1 border border-gray-700">
          <button
            onClick={() => setMode('backtest')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${mode === 'backtest'
              ? 'bg-blue-600 text-white shadow-lg'
              : 'text-gray-400 hover:text-gray-300'
              }`}
          >
            Backtest
          </button>
          <button
            onClick={() => setMode('favorites')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${mode === 'favorites'
              ? 'bg-amber-500 text-white shadow-lg shadow-amber-900/30'
              : 'text-gray-400 hover:text-gray-300'
              }`}
          >
            Favorites
          </button>
          <button
            onClick={() => setMode('optimization')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${mode === 'optimization'
              ? 'bg-purple-600 text-white shadow-lg'
              : 'text-gray-400 hover:text-gray-300'
              }`}
          >
            Optimization
          </button>
          <button
            onClick={() => setMode('data')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${mode === 'data'
              ? 'bg-emerald-600 text-white shadow-lg'
              : 'text-gray-400 hover:text-gray-300'
              }`}
          >
            Data
          </button>
        </div>

      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6 p-4 bg-red-900/30 border border-red-700/50 rounded-lg text-red-400">
          {error}
          <button
            onClick={() => setError('')}
            className="ml-4 text-red-300 hover:text-red-200"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Backtest Mode */}
      {mode === 'backtest' && (
        <div className="space-y-6">
          <Sidebar
            availableData={availableData}
            selectedSymbol={selectedSymbol}
            setSelectedSymbol={setSelectedSymbol}
            interval={interval}
            setInterval={setInterval}
            startDatetime={startDatetime}
            setStartDatetime={setStartDatetime}
            endDatetime={endDatetime}
            setEndDatetime={setEndDatetime}
            initialEquity={initialEquity}
            setInitialEquity={setInitialEquity}
            riskPerTrade={riskPerTrade}
            setRiskPerTrade={setRiskPerTrade}
            maxContracts={maxContracts}
            setMaxContracts={setMaxContracts}
            engineSettings={engineSettings}
            setEngineSettings={setEngineSettings}
            strategies={strategies}
            selectedStrategy={selectedStrategy}
            selectStrategy={selectStrategy}
            params={params}
            setParams={setParams}
            runBacktest={runBacktest}
            loading={loading}
            error={error}
            autoUpdate={autoUpdate}
            setAutoUpdate={setAutoUpdate}
            autoUpdateLoading={autoUpdateLoading}
            hasResult={result !== null}
          />

          <Dashboard
            filteredResult={filteredResult}
            selectedSessions={selectedSessions}
            onSessionsChange={setSelectedSessions}
            dataSource="Local"
            initialEquity={initialEquity}
            autoUpdate={autoUpdate}
            autoUpdateLoading={autoUpdateLoading}
            previousMetrics={previousMetrics}
          />
        </div>
      )}

      {/* Data Management Mode */}
      {mode === 'data' && (
        <MarketDataPanel />
      )}

      {/* Favorites Mode */}
      {mode === 'favorites' && (
        <FavoritesPage onLoadPreset={handleLoadFavoritePreset} />
      )}

      {/* Optimization Mode */}
      {mode === 'optimization' && (
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="glass-panel rounded-2xl p-16 flex flex-col items-center text-center max-w-lg w-full">
            <div className="relative mb-8">
              <div className="w-20 h-20 rounded-full bg-purple-600/15 border border-purple-500/20 flex items-center justify-center">
                <svg className="w-10 h-10 text-purple-400/70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-amber-500/80 border-2 border-[#0B0F19] flex items-center justify-center">
                <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
              </div>
            </div>
            <h2 className="text-2xl font-bold bg-gradient-to-r from-purple-400 via-indigo-400 to-blue-400 bg-clip-text text-transparent mb-3">
              Coming Soon
            </h2>
            <p className="text-gray-500 text-sm leading-relaxed">
              Le module d'optimisation est en cours de refonte.<br />
              Il sera disponible dans une prochaine version.
            </p>
            <div className="mt-8 flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-purple-500/50 animate-pulse" />
              <div className="w-1.5 h-1.5 rounded-full bg-purple-500/50 animate-pulse" style={{ animationDelay: '0.2s' }} />
              <div className="w-1.5 h-1.5 rounded-full bg-purple-500/50 animate-pulse" style={{ animationDelay: '0.4s' }} />
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}

export default App;
