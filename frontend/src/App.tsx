import { useState, useEffect, useCallback } from 'react';
import { api, type Strategy, type BacktestResult, type Contract, type Trade, type BacktestMetrics, type OptimizationResponse, type OptimizationResultItem, type ParameterRangeInput, type OptimizationRunDetail } from './api';
import './App.css';

// Components
import { Layout } from './components/Layout';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './components/Dashboard';
import { OptimizationConfig } from './components/OptimizationConfig';
import { OptimizationResults } from './components/OptimizationResults';
import { OptimizationHistory } from './components/OptimizationHistory';

// Type for strategy parameters
type StrategyParams = Record<string, number | string | boolean>;

// App modes
type AppMode = 'backtest' | 'optimization';
type OptimizationView = 'config' | 'results';

function App() {
  // Mode state
  const [mode, setMode] = useState<AppMode>('backtest');
  const [optimizationView, setOptimizationView] = useState<OptimizationView>('config');

  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [params, setParams] = useState<StrategyParams>({});

  // Data Config
  const [dataSource, setDataSource] = useState<'Yahoo' | 'Topstep'>('Yahoo');
  const [ticker, setTicker] = useState('BTC-USD');
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [selectedContract, setSelectedContract] = useState<Contract | null>(null);
  const [interval, setInterval] = useState('15m');
  const [days, setDays] = useState(14);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30); // 30 days before end date (inclusive range = 30 days?)
    // User wants "30 days full". If End=29, Start=31/12/25.
    // 29 Jan - 31 Dec = 29 days difference. Inclusive = 30 days.
    // Today (30 Jan) - 1 = 29 Jan.
    // Today (30 Jan) - ? = 31 Dec.
    // 30 Jan - 30 days = 31 Dec?
    // Jan has 31 days. 30 Jan - 30 days -> 31 Dec?
    // Jan 1 is 29 days diff.
    // Dec 31 is 30 days diff.
    // So 30 is correct.
    return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 1); // Yesterday
    return d.toISOString().split('T')[0];
  });
  const [topstepLiveMode, setTopstepLiveMode] = useState(true);
  const [manualContractId, setManualContractId] = useState('');

  // Risk Mgmt
  const [initialEquity, setInitialEquity] = useState(50000);
  const [riskPerTrade, setRiskPerTrade] = useState(1.0); // %

  // Trade Filters
  const [maxContracts, setMaxContracts] = useState(50);
  const [blockMarketOpen, setBlockMarketOpen] = useState(true);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState('');

  // Filters
  const [selectedSessions, setSelectedSessions] = useState<string[]>(['Asia', 'UK', 'US']);

  // Derived state
  const [filteredResult, setFilteredResult] = useState<BacktestResult | null>(null);

  // Optimization state
  const [optimizationResult, setOptimizationResult] = useState<OptimizationResponse | null>(null);
  const [optimizationLoading, setOptimizationLoading] = useState(false);
  // Store optimization config to transfer to backtest
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

  useEffect(() => {
    api.getStrategies().then(data => {
      setStrategies(data);
      if (data.length > 0) selectStrategy(data[0]);
    }).catch((err: unknown) => {
      const message = err instanceof Error ? err.message : String(err);
      setError("Failed to load strategies: " + message);
    });
  }, []);

  // Fetch Topstep contracts when source changes
  useEffect(() => {
    if (dataSource === 'Topstep' && contracts.length === 0) {
      setLoading(true);
      api.getTopstepContracts()
        .then(data => {
          setContracts(data);
          if (data.length > 0) setSelectedContract(data[0]);
        })
        .catch((err: unknown) => {
          const message = err instanceof Error ? err.message : String(err);
          setError("Topstep Error: " + message);
        })
        .finally(() => setLoading(false));
    }
  }, [dataSource, contracts.length]);

  const selectStrategy = useCallback((strat: Strategy) => {
    setSelectedStrategy(strat);
    setParams({ ...strat.default_params });
  }, []);

  const runBacktest = async () => {
    if (!selectedStrategy) return;
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const res = await api.runBacktest(
        selectedStrategy.name,
        ticker,
        dataSource,
        topstepLiveMode ? (selectedContract?.id || null) : manualContractId,
        interval,
        days,
        initialEquity,
        riskPerTrade / 100, // Send as decimal
        params,
        maxContracts,
        blockMarketOpen,
        startDate,
        endDate,
        topstepLiveMode
      );
      setResult(res);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

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
      sharpe_ratio: 0 // Hard to recalc without timeseries
    };
  }, []);

  useEffect(() => {
    if (!result) {
      setFilteredResult(null);
      return;
    }

    const filteredTrades = result.trades.filter(t => selectedSessions.includes(t.session));
    const newMetrics = calculateMetrics(filteredTrades, initialEquity);

    let currentEq = initialEquity;
    const newCurve = [{ time: 'Start', value: initialEquity }];
    filteredTrades.forEach((t, i) => {
      currentEq += t.pnl;
      newCurve.push({ time: t.exit_time || String(i), value: currentEq });
    });

    setFilteredResult({
      metrics: { ...result.metrics, ...newMetrics },
      trades: filteredTrades,
      equity_curve: newCurve
    });

  }, [result, selectedSessions, initialEquity, calculateMetrics]);

  const toggleSession = useCallback((sess: string) => {
    setSelectedSessions(prev =>
      prev.includes(sess)
        ? prev.filter(s => s !== sess)
        : [...prev, sess]
    );
  }, []);

  // Calculate session stats for summary table
  const sessionStats = ['Asia', 'UK', 'US'].map(sess => {
    if (!result) return null;
    const trades = result.trades.filter(t => t.session === sess);
    const metrics = calculateMetrics(trades, initialEquity);
    return { session: sess, ...metrics };
  }).filter((s): s is NonNullable<typeof s> => Boolean(s));

  // Fetch contracts callback for optimization mode
  const fetchContractsIfNeeded = useCallback(() => {
    if (contracts.length === 0) {
      setLoading(true);
      api.getTopstepContracts()
        .then(data => {
          setContracts(data);
          if (data.length > 0) setSelectedContract(data[0]);
        })
        .catch((err: unknown) => {
          const message = err instanceof Error ? err.message : String(err);
          setError("Topstep Error: " + message);
        })
        .finally(() => setLoading(false));
    }
  }, [contracts.length]);

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
      // Store config for transferring to backtest later
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
    // Find the strategy
    const strat = strategies.find(s => s.name === optimizationResult?.strategy_name);
    if (strat) {
      setSelectedStrategy(strat);

      // Set the parameters from the optimization result
      const newParams = { ...strat.default_params };
      Object.entries(result.parameters).forEach(([key, value]) => {
        newParams[key] = value;
      });
      setParams(newParams);

      // Set sessions
      setSelectedSessions(result.sessions);

      // Transfer ALL config from the optimization run
      if (lastOptimizationConfig) {
        setTicker(lastOptimizationConfig.ticker);
        setDataSource(lastOptimizationConfig.source);
        setInterval(lastOptimizationConfig.interval);
        setDays(lastOptimizationConfig.days);
        setInitialEquity(lastOptimizationConfig.initialEquity);
        setRiskPerTrade(lastOptimizationConfig.riskPerTrade * 100); // Convert back to percentage
        setMaxContracts(lastOptimizationConfig.maxContracts);
        setBlockMarketOpen(lastOptimizationConfig.blockMarketOpen);
        if (lastOptimizationConfig.startDate) setStartDate(lastOptimizationConfig.startDate);
        if (lastOptimizationConfig.endDate) setEndDate(lastOptimizationConfig.endDate);
        if (lastOptimizationConfig.topstepLiveMode !== undefined) setTopstepLiveMode(lastOptimizationConfig.topstepLiveMode);

        // Set the contract if Topstep
        if (lastOptimizationConfig.source === 'Topstep') {
          if (lastOptimizationConfig.topstepLiveMode) {
            setManualContractId(''); // Clear manual
            if (lastOptimizationConfig.contractId) {
              const contract = contracts.find(c => c.id === lastOptimizationConfig.contractId);
              if (contract) {
                setSelectedContract(contract);
              }
            }
          } else {
            // Legacy
            setSelectedContract(null); // Clear active
            if (lastOptimizationConfig.contractId) {
              setManualContractId(lastOptimizationConfig.contractId);
            }
          }
        }
      }

      // Switch to backtest mode
      setMode('backtest');
      setResult(null);
      setFilteredResult(null);
    }
  }, [strategies, optimizationResult, lastOptimizationConfig, contracts]);

  const handleBackFromResults = useCallback(() => {
    setOptimizationView('config');
  }, []);

  // Handler to load a historical optimization run
  const handleLoadHistoryRun = useCallback((run: OptimizationRunDetail) => {
    // Convert the run detail to an OptimizationResponse format
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

    // Store config for transferring to backtest later
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
    // Create config object from run details
    // Note: Some fields like initialEquity/risk might be missing if not saved in older runs
    // We will use defaults for those if missing

    const liveMode = run.topstep_live_mode !== undefined ? run.topstep_live_mode : true;

    setConfigToReuse({
      strategyName: run.strategy_name,
      ticker: run.ticker || 'BTC-USD',
      source: run.source as 'Yahoo' | 'Topstep',
      contractId: run.contract_id,
      interval: run.interval,
      days: run.days,
      parameters: run.parameters || [], // If empty/undefined, it will just load default params
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
              // Keep the current view (config or results) when switching back
              // Only reset to config if there's no result yet
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
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <Sidebar
            dataSource={dataSource}
            setDataSource={(v) => setDataSource(v as 'Yahoo' | 'Topstep')}
            ticker={ticker}
            setTicker={setTicker}
            contracts={contracts}
            selectedContract={selectedContract}
            setSelectedContract={setSelectedContract}
            interval={interval}
            setInterval={setInterval}
            days={days}
            setDays={setDays}
            initialEquity={initialEquity}
            setInitialEquity={setInitialEquity}
            riskPerTrade={riskPerTrade}
            setRiskPerTrade={setRiskPerTrade}
            maxContracts={maxContracts}
            setMaxContracts={setMaxContracts}
            blockMarketOpen={blockMarketOpen}
            setBlockMarketOpen={setBlockMarketOpen}
            startDate={startDate}
            setStartDate={setStartDate}
            endDate={endDate}
            setEndDate={setEndDate}
            topstepLiveMode={topstepLiveMode}
            setTopstepLiveMode={setTopstepLiveMode}
            manualContractId={manualContractId}
            setManualContractId={setManualContractId}
            strategies={strategies}
            selectedStrategy={selectedStrategy}
            selectStrategy={selectStrategy}
            params={params}
            setParams={setParams}
            runBacktest={runBacktest}
            loading={loading}
            error={error}
          />

          <div className="lg:col-span-3">
            <Dashboard
              filteredResult={filteredResult}
              selectedSessions={selectedSessions}
              toggleSession={toggleSession}
              dataSource={dataSource}
              initialEquity={initialEquity}
              sessionStats={sessionStats}
            />
          </div>
        </div>
      )}

      {/* Optimization Mode */}
      {mode === 'optimization' && (
        <>
          {optimizationView === 'config' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <OptimizationConfig
                strategies={strategies}
                contracts={contracts}
                onRunOptimization={handleRunOptimization}
                loading={optimizationLoading}
                onContractsNeeded={fetchContractsIfNeeded}
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
