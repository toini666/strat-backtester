import { useState, useEffect, useCallback, useRef } from 'react';
import {
  api,
  type Strategy,
  type BacktestResult,
  type AvailableDataset,
  type Trade,
  type BacktestMetrics,
  type OptimizationResponse,
  type OptimizationResultItem,
  type ParameterRangeInput,
  type OptimizationRunDetail,
  type BacktestEngineSettings,
  DEFAULT_BACKTEST_ENGINE_SETTINGS,
} from './api';

type BacktestContext = { symbol: string; interval: string; start: string; end: string };
import './App.css';

// Components
import { Layout } from './components/Layout';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './components/Dashboard';
import { OptimizationConfig } from './components/OptimizationConfig';
import { OptimizationResults } from './components/OptimizationResults';
import { OptimizationHistory } from './components/OptimizationHistory';
import { MarketDataPanel } from './components/MarketDataPanel';

// Type for strategy parameters
type StrategyParams = Record<string, number | string | boolean>;

// App modes
type AppMode = 'backtest' | 'optimization' | 'data';
type OptimizationView = 'config' | 'results';

function App() {
  // Mode state
  const [mode, setMode] = useState<AppMode>('backtest');
  const [optimizationView, setOptimizationView] = useState<OptimizationView>('config');

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
  const [, setBlockMarketOpen] = useState(true);
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

  // Optimization state
  const [optimizationResult, setOptimizationResult] = useState<OptimizationResponse | null>(null);
  const [optimizationLoading, setOptimizationLoading] = useState(false);
  const [lastOptimizationConfig, setLastOptimizationConfig] = useState<{
    ticker: string;
    source: 'Yahoo' | 'Topstep';
    contractId: string | null;
    interval: string;
    days: number;
    initialEquity: number;
    riskPerTrade: number;
    maxContracts: number;
    blockMarketOpen: boolean;
    startDate?: string;
    endDate?: string;
    topstepLiveMode?: boolean;
  } | null>(null);

  // Config to reuse for optimization
  const [configToReuse, setConfigToReuse] = useState<{
    strategyName: string;
    ticker: string;
    source: 'Yahoo' | 'Topstep';
    contractId: string | null;
    interval: string;
    days: number;
    parameters: ParameterRangeInput[];
    sessions: string[];
    initialEquity: number;
    riskPerTrade: number;
    maxContracts: number;
    blockMarketOpen: boolean;
    startDate?: string;
    endDate?: string;
    topstepLiveMode?: boolean;
    maxDrawdownLimit?: number;
    minWinRate?: number;
  } | null>(null);

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


  // Optimization handlers
  const handleRunOptimization = useCallback(async (config: {
    strategyName: string;
    ticker: string;
    source: 'Yahoo' | 'Topstep';
    contractId: string | null;
    interval: string;
    days: number;
    parameters: ParameterRangeInput[];
    sessions: string[];
    initialEquity: number;
    riskPerTrade: number;
    maxContracts: number;
    blockMarketOpen: boolean;
    startDate?: string;
    endDate?: string;
    topstepLiveMode?: boolean;
    maxDrawdownLimit?: number;
    minWinRate?: number;
  }) => {
    setOptimizationLoading(true);
    setError('');

    try {
      const res = await api.runOptimization({
        ...config,
        maxWorkers: 4
      });
      setOptimizationResult(res);
      setOptimizationView('results');
      setLastOptimizationConfig({
        ticker: config.ticker,
        source: config.source,
        contractId: config.contractId,
        interval: config.interval,
        days: config.days,
        initialEquity: config.initialEquity,
        riskPerTrade: config.riskPerTrade,
        maxContracts: config.maxContracts,
        blockMarketOpen: config.blockMarketOpen,
        startDate: config.startDate,
        endDate: config.endDate,
        topstepLiveMode: config.topstepLiveMode
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
    } finally {
      setOptimizationLoading(false);
    }
  }, []);

  const handleSelectOptimizationResult = useCallback((result: OptimizationResultItem) => {
    const strat = strategies.find(s => s.name === optimizationResult?.strategy_name);
    if (strat) {
      setSelectedStrategy(strat);

      const newParams = { ...strat.default_params };
      Object.entries(result.parameters).forEach(([key, value]) => {
        newParams[key] = value;
      });
      setParams(newParams);

      setSelectedSessions(result.sessions);

      if (lastOptimizationConfig) {
        setInterval(lastOptimizationConfig.interval);
        setInitialEquity(lastOptimizationConfig.initialEquity);
        setRiskPerTrade(lastOptimizationConfig.riskPerTrade * 100);
        setMaxContracts(lastOptimizationConfig.maxContracts);
        setBlockMarketOpen(lastOptimizationConfig.blockMarketOpen);
      }

      setMode('backtest');
      setResult(null);
      setFilteredResult(null);
    }
  }, [strategies, optimizationResult, lastOptimizationConfig]);

  const handleBackFromResults = useCallback(() => {
    setOptimizationView('config');
  }, []);

  const handleLoadHistoryRun = useCallback((run: OptimizationRunDetail) => {
    const response: OptimizationResponse = {
      id: run.id,
      strategy_name: run.strategy_name,
      total_combinations: run.total_combinations,
      completed: run.total_combinations,
      top_results: run.top_results,
      errors: 0
    };
    setOptimizationResult(response);
    setOptimizationView('results');

    setLastOptimizationConfig({
      ticker: run.ticker,
      source: run.source as 'Yahoo' | 'Topstep',
      contractId: run.contract_id,
      interval: run.interval,
      days: run.days,
      initialEquity: run.initial_equity || 50000,
      riskPerTrade: run.risk_per_trade !== undefined ? run.risk_per_trade : 0.01,
      maxContracts: 50,
      blockMarketOpen: true,
      startDate: run.start_date,
      endDate: run.end_date,
      topstepLiveMode: run.topstep_live_mode !== undefined ? run.topstep_live_mode : true
    });
  }, []);

  const handleReuseHistoryConfig = useCallback((run: OptimizationRunDetail) => {
    const liveMode = run.topstep_live_mode !== undefined ? run.topstep_live_mode : true;

    setConfigToReuse({
      strategyName: run.strategy_name,
      ticker: run.ticker || 'BTC-USD',
      source: run.source as 'Yahoo' | 'Topstep',
      contractId: run.contract_id,
      interval: run.interval,
      days: run.days,
      parameters: run.parameters || [],
      sessions: run.sessions_tested,
      initialEquity: run.initial_equity || 50000,
      riskPerTrade: run.risk_per_trade !== undefined ? run.risk_per_trade : 0.01,
      maxContracts: 50,
      blockMarketOpen: true,
      startDate: run.start_date,
      endDate: run.end_date,
      topstepLiveMode: liveMode,
      maxDrawdownLimit: run.max_drawdown_limit,
      minWinRate: run.min_win_rate,
    });

    setOptimizationResult(null);
    setOptimizationView('config');
  }, []);

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
            onClick={() => {
              setMode('optimization');
              if (!optimizationResult) {
                setOptimizationView('config');
              }
            }}
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

        {mode === 'optimization' && optimizationResult && (
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-500">
              {optimizationView === 'results'
                ? `Viewing optimization results for ${optimizationResult?.strategy_name}`
                : `Results available for ${optimizationResult?.strategy_name}`}
            </span>
            <button
              onClick={() => {
                setOptimizationResult(null);
                setLastOptimizationConfig(null);
                setOptimizationView('config');
              }}
              className="text-xs px-3 py-1 rounded bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-300 transition-colors"
            >
              Reset
            </button>
            {optimizationView === 'config' && (
              <button
                onClick={() => setOptimizationView('results')}
                className="text-xs px-3 py-1 rounded bg-purple-800 text-purple-300 hover:bg-purple-700 hover:text-purple-200 transition-colors"
              >
                View Results
              </button>
            )}
          </div>
        )}
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

      {/* Optimization Mode */}
      {mode === 'optimization' && (
        <>
          {optimizationView === 'config' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <OptimizationConfig
                strategies={strategies}
                contracts={[]}
                onRunOptimization={handleRunOptimization}
                loading={optimizationLoading}
                onContractsNeeded={() => {}}
                initialConfig={configToReuse}
              />

              <div className="lg:col-span-2 space-y-6">
                <div className="glass-panel rounded-xl p-6">
                  <div className="flex flex-col items-center justify-center text-center py-4">
                    <div className="w-16 h-16 rounded-full bg-purple-600/20 flex items-center justify-center mb-4">
                      <svg className="w-8 h-8 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-300 mb-2">Parameter Optimization</h3>
                    <p className="text-gray-500 text-sm max-w-md">
                      Test multiple parameter combinations and session configurations to find the optimal strategy settings.
                    </p>
                  </div>
                </div>

                <OptimizationHistory
                  onLoadRun={handleLoadHistoryRun}
                  onReuseRun={handleReuseHistoryConfig}
                />
              </div>
            </div>
          )}

          {optimizationView === 'results' && optimizationResult && (
            <OptimizationResults
              results={optimizationResult.top_results}
              strategyName={optimizationResult.strategy_name}
              totalCombinations={optimizationResult.total_combinations}
              completed={optimizationResult.completed}
              errors={optimizationResult.errors}
              config={lastOptimizationConfig || undefined}
              onSelectResult={handleSelectOptimizationResult}
              onBack={handleBackFromResults}
            />
          )}
        </>
      )}
    </Layout>
  );
}

export default App;
