import { useState, useEffect, useCallback } from 'react';
import { api, type Strategy, type BacktestResult, type Contract, type Trade, type BacktestMetrics, type OptimizationResponse, type OptimizationResultItem, type ParameterRangeInput } from './api';
import './App.css';

// Components
import { Layout } from './components/Layout';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './components/Dashboard';
import { OptimizationConfig } from './components/OptimizationConfig';
import { OptimizationResults } from './components/OptimizationResults';

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

  // Risk Mgmt
  const [initialEquity, setInitialEquity] = useState(50000);
  const [riskPerTrade, setRiskPerTrade] = useState(1.0); // %

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
        selectedContract?.id || null,
        interval,
        days,
        initialEquity,
        riskPerTrade / 100, // Send as decimal
        params
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

      // Switch to backtest mode
      setMode('backtest');
      setResult(null);
      setFilteredResult(null);
    }
  }, [strategies, optimizationResult]);

  const handleBackFromResults = useCallback(() => {
    setOptimizationView('config');
  }, []);

  return (
    <Layout>
      {/* Mode Toggle */}
      <div className="mb-6 flex items-center gap-4">
        <div className="inline-flex rounded-lg bg-gray-800/50 p-1 border border-gray-700">
          <button
            onClick={() => setMode('backtest')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
              mode === 'backtest'
                ? 'bg-blue-600 text-white shadow-lg'
                : 'text-gray-400 hover:text-gray-300'
            }`}
          >
            Backtest
          </button>
          <button
            onClick={() => {
              setMode('optimization');
              setOptimizationView('config');
            }}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
              mode === 'optimization'
                ? 'bg-purple-600 text-white shadow-lg'
                : 'text-gray-400 hover:text-gray-300'
            }`}
          >
            Optimization
          </button>
        </div>

        {mode === 'optimization' && optimizationView === 'results' && (
          <span className="text-sm text-gray-500">
            Viewing optimization results for {optimizationResult?.strategy_name}
          </span>
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
              />

              <div className="lg:col-span-2">
                <div className="glass-panel rounded-xl p-8 h-full flex flex-col items-center justify-center text-center">
                  <div className="w-20 h-20 rounded-full bg-purple-600/20 flex items-center justify-center mb-6">
                    <svg className="w-10 h-10 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                  </div>
                  <h3 className="text-xl font-semibold text-gray-300 mb-3">Parameter Optimization</h3>
                  <p className="text-gray-500 max-w-md mb-6">
                    Test multiple parameter combinations and session configurations to find the optimal strategy settings.
                  </p>
                  <div className="space-y-2 text-sm text-gray-600">
                    <p>1. Select a strategy and configure parameter ranges</p>
                    <p>2. Choose which sessions to test (all combinations)</p>
                    <p>3. Run optimization to find the best configurations</p>
                    <p>4. Click on results to run full backtests</p>
                  </div>
                </div>
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
