import { useState, useEffect } from 'react';
import { api, type Strategy, type BacktestResult, type Contract } from './api';
import './App.css';

// Components
import { Layout } from './components/Layout';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './components/Dashboard';

function App() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [params, setParams] = useState<Record<string, any>>({});

  // Data Config
  const [dataSource, setDataSource] = useState('Yahoo'); // Yahoo or Topstep
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

  useEffect(() => {
    api.getStrategies().then(data => {
      setStrategies(data);
      if (data.length > 0) selectStrategy(data[0]);
    }).catch(err => setError("Failed to load strategies: " + err.message));
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
        .catch(err => setError("Topstep Error: " + (err.response?.data?.detail || err.message)))
        .finally(() => setLoading(false));
    }
  }, [dataSource]);

  const selectStrategy = (strat: Strategy) => {
    setSelectedStrategy(strat);
    setParams({ ...strat.default_params });
  };

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
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  // Helper to calc metrics on a subset of trades
  const calculateMetrics = (trades: any[], initialEquity: number) => {
    let equity = initialEquity;
    let peak = initialEquity;
    let maxDrawdown = 0;

    let cumPnL = 0;
    let winCount = 0;

    trades.forEach(t => {
      cumPnL += t.pnl;
      equity += t.pnl;
      if (equity > peak) peak = equity;
      const dd = (peak - equity) / peak;
      if (dd > maxDrawdown) maxDrawdown = dd;
      if (t.pnl > 0) winCount++;
    });

    return {
      total_return: (cumPnL / initialEquity) * 100,
      win_rate: trades.length > 0 ? (winCount / trades.length) * 100 : 0,
      total_trades: trades.length,
      max_drawdown: maxDrawdown * 100,
      sharpe_ratio: 0 // Hard to recalc without timeseries
    };
  };

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
      metrics: { ...result.metrics, ...newMetrics }, // Override metrics
      trades: filteredTrades,
      equity_curve: newCurve
    });

  }, [result, selectedSessions, initialEquity]);

  const toggleSession = (sess: string) => {
    if (selectedSessions.includes(sess)) {
      setSelectedSessions(prev => prev.filter(s => s !== sess));
    } else {
      setSelectedSessions(prev => [...prev, sess]);
    }
  };

  // Calculate session stats for summary table
  const sessionStats = ['Asia', 'UK', 'US'].map(sess => {
    if (!result) return null;
    const trades = result.trades.filter(t => t.session === sess);
    const metrics = calculateMetrics(trades, initialEquity);
    return { session: sess, ...metrics };
  }).filter((s): s is NonNullable<typeof s> => Boolean(s));

  return (
    <Layout>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Sidebar
          dataSource={dataSource} setDataSource={setDataSource}
          ticker={ticker} setTicker={setTicker}
          contracts={contracts} selectedContract={selectedContract} setSelectedContract={setSelectedContract}
          interval={interval} setInterval={setInterval}
          days={days} setDays={setDays}
          initialEquity={initialEquity} setInitialEquity={setInitialEquity}
          riskPerTrade={riskPerTrade} setRiskPerTrade={setRiskPerTrade}
          strategies={strategies} selectedStrategy={selectedStrategy} selectStrategy={selectStrategy}
          params={params} setParams={setParams}
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
    </Layout>
  );
}

export default App;
