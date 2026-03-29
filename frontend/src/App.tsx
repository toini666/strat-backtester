import { useState, useEffect, useCallback, useRef } from 'react';
import {
  api,
  type Strategy,
  type BacktestResult,
  type MultiBacktestResult,
  type MultiBacktestConfig,
  type BacktestMode,
  type SingleBacktestPreset,
  type MultiBacktestPreset,
  type BacktestPreset,
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
import { MarketDataPanel } from './components/MarketDataPanel';
import { FavoritesPage } from './components/FavoritesPage';

// Type for strategy parameters
type StrategyParams = Record<string, number | string | boolean>;

// App modes
type AppMode = 'backtest' | 'optimization' | 'data' | 'favorites';

function makeDefaultEngineSettings(): BacktestEngineSettings {
  return {
    ...DEFAULT_BACKTEST_ENGINE_SETTINGS,
    blackout_windows: DEFAULT_BACKTEST_ENGINE_SETTINGS.blackout_windows.map((w) => ({ ...w })),
  };
}

function App() {
  // App navigation mode
  const [mode, setMode] = useState<AppMode>('backtest');

  // Backtest mode: single / multi-asset / multi-strat
  const [backtestMode, setBacktestMode] = useState<BacktestMode>('single');
  // Which slot is active in multi mode (0 = first, 1 = second)
  const [activeSlot, setActiveSlot] = useState<0 | 1>(0);

  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [availableData, setAvailableData] = useState<AvailableDataset[]>([]);

  // ── Slot 1 state (always used in single mode; also the first config in multi mode) ──
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [params, setParams] = useState<StrategyParams>({});
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [interval, setInterval] = useState('5m');
  const [startDatetime, setStartDatetime] = useState('');
  const [endDatetime, setEndDatetime] = useState('');
  const [initialEquity, setInitialEquity] = useState(50000);
  const [riskPerTrade, setRiskPerTrade] = useState(0.5); // %
  const [maxContracts, setMaxContracts] = useState(50);
  const [engineSettings, setEngineSettings] = useState<BacktestEngineSettings>(makeDefaultEngineSettings());

  // ── Slot 2 state (second config in multi mode) ──
  const [selectedStrategy2, setSelectedStrategy2] = useState<Strategy | null>(null);
  const [params2, setParams2] = useState<StrategyParams>({});
  const [selectedSymbol2, setSelectedSymbol2] = useState('');
  const [interval2, setInterval2] = useState('5m');
  const [riskPerTrade2, setRiskPerTrade2] = useState(0.5);
  const [maxContracts2, setMaxContracts2] = useState(50);
  const [engineSettings2, setEngineSettings2] = useState<BacktestEngineSettings>(makeDefaultEngineSettings());

  const selectStrategy2 = useCallback((strat: Strategy) => {
    setSelectedStrategy2(strat);
    setParams2({ ...strat.default_params });
  }, []);

  // When switching to multi mode for the first time, copy slot 1 into slot 2 as a starting point
  const hasInitializedSlot2Ref = useRef(false);
  useEffect(() => {
    if (backtestMode !== 'single' && !hasInitializedSlot2Ref.current) {
      hasInitializedSlot2Ref.current = true;
      // In multi_asset, slot 2 must have a different symbol than slot 1
      if (backtestMode === 'multi_asset') {
        const other = availableData.find(d => d.symbol !== selectedSymbol);
        setSelectedSymbol2(other ? other.symbol : selectedSymbol);
      } else {
        setSelectedSymbol2(selectedSymbol);
      }
      setInterval2(interval);
      if (selectedStrategy) {
        setSelectedStrategy2(selectedStrategy);
        setParams2({ ...params });
      }
      setRiskPerTrade2(riskPerTrade);
      setMaxContracts2(maxContracts);
      setEngineSettings2(JSON.parse(JSON.stringify(engineSettings)));
    }
    if (backtestMode === 'single') {
      hasInitializedSlot2Ref.current = false;
    }
  }, [backtestMode]);

  // ── Results ──
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [multiResult, setMultiResult] = useState<MultiBacktestResult | null>(null);
  const [error, setError] = useState('');

  // Previous run comparison — tracks metrics from the last completed run (same context only)
  const [previousMetrics, setPreviousMetrics] = useState<BacktestMetrics | null>(null);
  const currentResultContextRef = useRef<BacktestContext | null>(null);
  const filteredResultRef = useRef<BacktestResult | null>(null);

  // Stale-result detection: hash of the config at last successful run
  const lastRunConfigHashRef = useRef<string | null>(null);
  // Ref that always holds the latest buildConfigHash function (updated each render)
  const buildConfigHashRef = useRef<() => string>(() => '');

  // Auto-update mode (single mode only)
  const [autoUpdate, setAutoUpdate] = useState(false);
  const [autoUpdateLoading, setAutoUpdateLoading] = useState(false);
  const autoUpdateTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Session filters
  const [selectedSessions, setSelectedSessions] = useState<string[]>(['Asia', 'UK', 'US']);

  // Derived/filtered results
  const [filteredResult, setFilteredResult] = useState<BacktestResult | null>(null);
  const [filteredMultiResult, setFilteredMultiResult] = useState<MultiBacktestResult | null>(null);

  // ── Load strategies & available data on mount ──
  useEffect(() => {
    api.getStrategies().then(data => {
      setStrategies(data);
      if (data.length > 0) selectStrategy(data[0]);
    }).catch((err: unknown) => {
      setError("Failed to load strategies: " + (err instanceof Error ? err.message : String(err)));
    });

    api.getAvailableData().then(data => {
      setAvailableData(data);
      if (data.length > 0) {
        setSelectedSymbol(data[0].symbol);
        if (data[0].timeframes.includes('5m')) {
          setInterval('5m');
        } else if (data[0].timeframes.length > 0) {
          setInterval(data[0].timeframes[data[0].timeframes.length - 1]);
        }
        setEndDatetime(data[0].end_date.slice(0, 16));
      }
    }).catch((err: unknown) => {
      setError("Failed to load available data: " + (err instanceof Error ? err.message : String(err)));
    });
  }, []);

  // Default start datetime for slot 1
  useEffect(() => {
    if (!selectedSymbol || !selectedStrategy || availableData.length === 0) return;
    const ds = availableData.find(d => d.symbol === selectedSymbol);
    if (!ds) return;
    const minStarts = ds.min_start_per_strategy[selectedStrategy.name];
    if (minStarts && minStarts[interval]) {
      const minStart = minStarts[interval];
      if (!startDatetime || startDatetime < minStart.slice(0, 16)) {
        setStartDatetime(minStart.slice(0, 16));
      }
    }
  }, [selectedSymbol, selectedStrategy, interval, availableData]);

  const selectStrategy = useCallback((strat: Strategy) => {
    setSelectedStrategy(strat);
    setParams({ ...strat.default_params });
  }, []);

  // ── Run Backtest ──
  const runBacktest = async () => {
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
    setMultiResult(null);

    try {
      if (backtestMode === 'single') {
        if (!selectedStrategy || !selectedSymbol) return;
        const res = await api.runBacktest(
          selectedStrategy.name,
          selectedSymbol,
          interval,
          startDatetime,
          endDatetime,
          initialEquity,
          riskPerTrade / 100,
          params,
          maxContracts,
          engineSettings,
        );
        setResult(res);
        lastRunConfigHashRef.current = buildConfigHashRef.current();
        currentResultContextRef.current = newContext;
        lastSignalParamsRef.current = JSON.stringify(params);
      } else {
        // Multi mode: build two configs
        if (!selectedStrategy || !selectedStrategy2) return;
        const cfg1: MultiBacktestConfig = {
          strategy_name: selectedStrategy.name,
          symbol: selectedSymbol,
          interval,
          params,
          risk_per_trade: riskPerTrade / 100,
          max_contracts: maxContracts,
          engine_settings: engineSettings,
        };
        const cfg2: MultiBacktestConfig = {
          strategy_name: selectedStrategy2.name,
          symbol: backtestMode === 'multi_strat' ? selectedSymbol : selectedSymbol2,
          interval: interval2,
          params: params2,
          risk_per_trade: riskPerTrade2 / 100,
          max_contracts: maxContracts2,
          engine_settings: engineSettings2,
        };
        const res = await api.runMultiBacktest(
          backtestMode,
          startDatetime,
          endDatetime,
          initialEquity,
          [cfg1, cfg2],
        );
        setMultiResult(res);
        lastRunConfigHashRef.current = buildConfigHashRef.current();
        currentResultContextRef.current = newContext;
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  // Keep filteredResultRef in sync
  useEffect(() => {
    filteredResultRef.current = filteredResult;
  }, [filteredResult]);

  // Multi-strat: slot 2 ticker always mirrors slot 1
  useEffect(() => {
    if (backtestMode === 'multi_strat') {
      setSelectedSymbol2(selectedSymbol);
    }
  }, [selectedSymbol, backtestMode]);

  // Clear previous metrics when context changes
  useEffect(() => {
    const ctx = currentResultContextRef.current;
    if (!ctx) return;
    if (selectedSymbol !== ctx.symbol || interval !== ctx.interval ||
        startDatetime !== ctx.start || endDatetime !== ctx.end) {
      setPreviousMetrics(null);
      currentResultContextRef.current = null;
    }
  }, [selectedSymbol, interval, startDatetime, endDatetime]);

  // Auto-update (single mode only): debounced re-run when parameters change
  const autoUpdateRef = useRef({
    initialEquity, riskPerTrade, maxContracts, params, engineSettings,
    selectedStrategy, selectedSymbol, interval, startDatetime, endDatetime,
  });
  autoUpdateRef.current = {
    initialEquity, riskPerTrade, maxContracts, params, engineSettings,
    selectedStrategy, selectedSymbol, interval, startDatetime, endDatetime,
  };
  const lastSignalParamsRef = useRef<string | null>(null);

  useEffect(() => {
    if (!autoUpdate || !result || backtestMode !== 'single') return;
    if (autoUpdateTimer.current) clearTimeout(autoUpdateTimer.current);
    autoUpdateTimer.current = setTimeout(async () => {
      const p = autoUpdateRef.current;
      if (!p.selectedStrategy || !p.selectedSymbol) return;

      const newContext: BacktestContext = { symbol: p.selectedSymbol, interval: p.interval, start: p.startDatetime, end: p.endDatetime };
      const ctx = currentResultContextRef.current;
      const fr = filteredResultRef.current;
      if (fr && ctx && ctx.symbol === newContext.symbol && ctx.interval === newContext.interval &&
          ctx.start === newContext.start && ctx.end === newContext.end) {
        setPreviousMetrics({ ...fr.metrics });
      } else {
        setPreviousMetrics(null);
      }

      const currentParamsKey = JSON.stringify(p.params);
      const needsFullBacktest = lastSignalParamsRef.current !== null
        && lastSignalParamsRef.current !== currentParamsKey;

      setAutoUpdateLoading(true);
      try {
        let res: BacktestResult;
        if (needsFullBacktest) {
          res = await api.runBacktest(
            p.selectedStrategy.name, p.selectedSymbol, p.interval,
            p.startDatetime, p.endDatetime, p.initialEquity,
            p.riskPerTrade / 100, p.params, p.maxContracts, p.engineSettings,
          );
          lastSignalParamsRef.current = currentParamsKey;
        } else {
          res = await api.resimulate(
            p.initialEquity, p.riskPerTrade / 100, p.maxContracts,
            p.params, p.engineSettings,
          );
        }
        setResult(res);
        lastRunConfigHashRef.current = buildConfigHashRef.current();
        currentResultContextRef.current = newContext;
        setError('');
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setAutoUpdateLoading(false);
      }
    }, 400);
    return () => { if (autoUpdateTimer.current) clearTimeout(autoUpdateTimer.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoUpdate, initialEquity, riskPerTrade, maxContracts, params, engineSettings]);

  // Helper: compute metrics from a trade list
  const calculateMetrics = useCallback((trades: Trade[], equity: number): BacktestMetrics => {
    let currentEquity = equity;
    let peak = equity;
    let maxDrawdown = 0;
    let maxDrawdownDollars = 0;
    let cumPnL = 0;
    let winCount = 0;
    trades.forEach(t => {
      cumPnL += t.pnl;
      currentEquity += t.pnl;
      if (currentEquity > peak) peak = currentEquity;
      const dd = (peak - currentEquity) / peak;
      if (dd > maxDrawdown) {
        maxDrawdown = dd;
        maxDrawdownDollars = peak - currentEquity;
      }
      if (t.pnl > 0) winCount++;
    });
    return {
      total_return: (cumPnL / equity) * 100,
      win_rate: trades.length > 0 ? (winCount / trades.length) * 100 : 0,
      total_trades: trades.length,
      max_drawdown: maxDrawdown * 100,
      max_drawdown_dollars: maxDrawdownDollars,
      sharpe_ratio: 0,
    };
  }, []);

  // Compute filteredResult from single-mode result
  useEffect(() => {
    if (!result) { setFilteredResult(null); return; }
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

  // Compute filteredMultiResult from multi-mode result
  useEffect(() => {
    if (!multiResult) { setFilteredMultiResult(null); return; }
    const filteredTrades = multiResult.trades.filter(t => selectedSessions.includes(t.session));
    const activeTrades = filteredTrades.filter(t => !t.excluded);
    const newMetrics = calculateMetrics(activeTrades, initialEquity);
    let currentEq = initialEquity;
    const newCurve = [{ time: 'Start', value: initialEquity }];
    activeTrades.forEach((t, i) => {
      currentEq += t.pnl;
      newCurve.push({ time: t.exit_execution_time || t.exit_time || String(i), value: currentEq });
    });
    setFilteredMultiResult({
      ...multiResult,
      metrics: { ...multiResult.metrics, ...newMetrics },
      trades: filteredTrades,
      equity_curve: newCurve,
    });
  }, [multiResult, selectedSessions, initialEquity, calculateMetrics]);

  // ── Load favorite preset ──
  const handleLoadFavoritePreset = useCallback((preset: BacktestPreset) => {
    if (preset.mode === 'multi_asset' || preset.mode === 'multi_strat') {
      // ── Load full multi preset ──
      const mp = preset as MultiBacktestPreset;
      const [c1, c2] = mp.configs;
      setBacktestMode(mp.mode);
      setStartDatetime(mp.startDatetime);
      setEndDatetime(mp.endDatetime);
      setInitialEquity(mp.initialEquity);
      // Slot 1
      const s1 = strategies.find(s => s.name === c1.strategyName);
      if (s1) { selectStrategy(s1); setTimeout(() => setParams({ ...s1.default_params, ...c1.params }), 0); }
      setSelectedSymbol(c1.symbol);
      setInterval(c1.interval);
      setRiskPerTrade(c1.riskPerTrade);
      setMaxContracts(c1.maxContracts);
      setEngineSettings(JSON.parse(JSON.stringify(c1.engineSettings)));
      // Slot 2
      const s2 = strategies.find(s => s.name === c2.strategyName);
      if (s2) { setSelectedStrategy2(s2); setTimeout(() => setParams2({ ...s2.default_params, ...c2.params }), 0); }
      setSelectedSymbol2(c2.symbol);
      setInterval2(c2.interval);
      setRiskPerTrade2(c2.riskPerTrade);
      setMaxContracts2(c2.maxContracts);
      setEngineSettings2(JSON.parse(JSON.stringify(c2.engineSettings)));
      hasInitializedSlot2Ref.current = true;
    } else if (backtestMode !== 'single') {
      // ── Apply single preset to the active slot (stay in multi mode) ──
      const sp = preset as SingleBacktestPreset;
      const strat = strategies.find(s => s.name === sp.strategyName);
      if (activeSlot === 0) {
        if (strat) { selectStrategy(strat); setTimeout(() => setParams({ ...strat.default_params, ...sp.params }), 0); }
        setSelectedSymbol(sp.symbol);
        setInterval(sp.interval);
        setRiskPerTrade(sp.riskPerTrade);
        setMaxContracts(sp.maxContracts);
        setEngineSettings(JSON.parse(JSON.stringify(sp.engineSettings)));
      } else {
        if (strat) { setSelectedStrategy2(strat); setTimeout(() => setParams2({ ...strat.default_params, ...sp.params }), 0); }
        // multi_asset: apply the preset's symbol; multi_strat: ticker is locked, don't change
        if (backtestMode === 'multi_asset') setSelectedSymbol2(sp.symbol);
        setInterval2(sp.interval);
        setRiskPerTrade2(sp.riskPerTrade);
        setMaxContracts2(sp.maxContracts);
        setEngineSettings2(JSON.parse(JSON.stringify(sp.engineSettings)));
      }
      // Dates and equity are shared — not changed
    } else {
      // ── Load single preset in single mode ──
      const sp = preset as SingleBacktestPreset;
      setBacktestMode('single');
      const strat = strategies.find(s => s.name === sp.strategyName);
      if (strat) { selectStrategy(strat); setTimeout(() => setParams({ ...strat.default_params, ...sp.params }), 0); }
      setSelectedSymbol(sp.symbol);
      setInterval(sp.interval);
      setStartDatetime(sp.startDatetime);
      setEndDatetime(sp.endDatetime);
      setInitialEquity(sp.initialEquity);
      setRiskPerTrade(sp.riskPerTrade);
      setMaxContracts(sp.maxContracts);
      setEngineSettings(JSON.parse(JSON.stringify(sp.engineSettings)));
    }
    setMode('backtest');
  }, [strategies, selectStrategy, backtestMode, activeSlot]);

  // Build multi preset for saving from Sidebar
  const buildMultiPreset = useCallback((): MultiBacktestPreset | null => {
    if (!selectedStrategy || !selectedStrategy2) return null;
    return {
      id: crypto.randomUUID(),
      name: `${backtestMode === 'multi_asset' ? 'Multi-Asset' : 'Multi-Strat'} — ${selectedSymbol}/${selectedSymbol2}`,
      createdAt: new Date().toISOString(),
      mode: backtestMode as 'multi_asset' | 'multi_strat',
      startDatetime,
      endDatetime,
      initialEquity,
      configs: [
        {
          symbol: selectedSymbol, interval, strategyName: selectedStrategy.name,
          params, riskPerTrade, maxContracts, engineSettings,
        },
        {
          symbol: backtestMode === 'multi_strat' ? selectedSymbol : selectedSymbol2,
          interval: interval2, strategyName: selectedStrategy2.name,
          params: params2, riskPerTrade: riskPerTrade2, maxContracts: maxContracts2,
          engineSettings: engineSettings2,
        },
      ],
    };
  }, [backtestMode, selectedSymbol, selectedSymbol2, interval, interval2, selectedStrategy, selectedStrategy2,
      params, params2, riskPerTrade, riskPerTrade2, maxContracts, maxContracts2, engineSettings, engineSettings2,
      startDatetime, endDatetime, initialEquity]);

  // Determine which slot's state to pass to Sidebar
  const isMulti = backtestMode !== 'single';
  const showSlot1 = !isMulti || activeSlot === 0;

  const sidebarSymbol = showSlot1 ? selectedSymbol : selectedSymbol2;
  const sidebarSetSymbol = showSlot1
    ? setSelectedSymbol
    : (backtestMode === 'multi_strat' ? (_: string) => {} : setSelectedSymbol2);
  const sidebarInterval = showSlot1 ? interval : interval2;
  const sidebarSetInterval = showSlot1 ? setInterval : setInterval2;
  const sidebarStrategy = showSlot1 ? selectedStrategy : selectedStrategy2;
  const sidebarSelectStrategy = showSlot1 ? selectStrategy : selectStrategy2;
  const sidebarParams = showSlot1 ? params : params2;
  const sidebarSetParams = showSlot1 ? setParams : setParams2;
  const sidebarRiskPerTrade = showSlot1 ? riskPerTrade : riskPerTrade2;
  const sidebarSetRiskPerTrade = showSlot1 ? setRiskPerTrade : setRiskPerTrade2;
  const sidebarMaxContracts = showSlot1 ? maxContracts : maxContracts2;
  const sidebarSetMaxContracts = showSlot1 ? setMaxContracts : setMaxContracts2;
  const sidebarEngineSettings = showSlot1 ? engineSettings : engineSettings2;
  const sidebarSetEngineSettings = showSlot1 ? setEngineSettings : setEngineSettings2;

  // Build a stable hash of the current backtest config (used for stale-result detection)
  const buildConfigHash = () => JSON.stringify(
    backtestMode === 'single'
      ? { mode: 'single', strategy: selectedStrategy?.name, symbol: selectedSymbol, interval,
          start: startDatetime, end: endDatetime, equity: initialEquity,
          risk: riskPerTrade, maxContracts, params, engine: engineSettings }
      : { mode: backtestMode,
          strategy1: selectedStrategy?.name, symbol1: selectedSymbol, interval1: interval,
          params1: params, risk1: riskPerTrade, maxContracts1: maxContracts, engine1: engineSettings,
          strategy2: selectedStrategy2?.name,
          symbol2: backtestMode === 'multi_strat' ? selectedSymbol : selectedSymbol2,
          interval2, params2, risk2: riskPerTrade2, maxContracts2: maxContracts2, engine2: engineSettings2,
          start: startDatetime, end: endDatetime, equity: initialEquity }
  );

  // Keep the ref in sync so runBacktest (async) can always read the latest hash
  buildConfigHashRef.current = buildConfigHash;

  const hasResult = filteredResult !== null || filteredMultiResult !== null;
  const resultIsStale = hasResult &&
    lastRunConfigHashRef.current !== null &&
    lastRunConfigHashRef.current !== buildConfigHash();

  // In multi_asset, the other slot's symbol (to prevent duplicate selection)
  const sidebarOtherSymbol = isMulti && backtestMode === 'multi_asset'
    ? (activeSlot === 0 ? selectedSymbol2 : selectedSymbol)
    : undefined;

  const canRun = backtestMode === 'single'
    ? !!(selectedStrategy && selectedSymbol)
    : !!(selectedStrategy && selectedStrategy2);

  return (
    <Layout>
      {/* App navigation toggle */}
      <div className="mb-6 flex items-center gap-4">
        <div className="inline-flex rounded-lg bg-gray-800/50 p-1 border border-gray-700">
          <button
            onClick={() => setMode('backtest')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${mode === 'backtest'
              ? 'bg-blue-600 text-white shadow-lg'
              : 'text-gray-400 hover:text-gray-300'}`}
          >
            Backtest
          </button>
          <button
            onClick={() => setMode('favorites')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${mode === 'favorites'
              ? 'bg-amber-500 text-white shadow-lg shadow-amber-900/30'
              : 'text-gray-400 hover:text-gray-300'}`}
          >
            Favorites
          </button>
          <button
            onClick={() => setMode('optimization')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${mode === 'optimization'
              ? 'bg-purple-600 text-white shadow-lg'
              : 'text-gray-400 hover:text-gray-300'}`}
          >
            Optimization
          </button>
          <button
            onClick={() => setMode('data')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${mode === 'data'
              ? 'bg-emerald-600 text-white shadow-lg'
              : 'text-gray-400 hover:text-gray-300'}`}
          >
            Data
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6 p-4 bg-red-900/30 border border-red-700/50 rounded-lg text-red-400">
          {error}
          <button onClick={() => setError('')} className="ml-4 text-red-300 hover:text-red-200">
            Dismiss
          </button>
        </div>
      )}

      {/* Backtest Mode */}
      {mode === 'backtest' && (
        <div className="space-y-6">
          <Sidebar
            availableData={availableData}
            selectedSymbol={sidebarSymbol}
            setSelectedSymbol={sidebarSetSymbol}
            symbolLocked={isMulti && activeSlot === 1 && backtestMode === 'multi_strat'}
            otherSymbol={sidebarOtherSymbol}
            interval={sidebarInterval}
            setInterval={sidebarSetInterval}
            startDatetime={startDatetime}
            setStartDatetime={setStartDatetime}
            endDatetime={endDatetime}
            setEndDatetime={setEndDatetime}
            datesReadOnly={isMulti && activeSlot === 1}
            initialEquity={initialEquity}
            setInitialEquity={setInitialEquity}
            equityReadOnly={isMulti && activeSlot === 1}
            riskPerTrade={sidebarRiskPerTrade}
            setRiskPerTrade={sidebarSetRiskPerTrade}
            maxContracts={sidebarMaxContracts}
            setMaxContracts={sidebarSetMaxContracts}
            engineSettings={sidebarEngineSettings}
            setEngineSettings={sidebarSetEngineSettings}
            strategies={strategies}
            selectedStrategy={sidebarStrategy}
            selectStrategy={sidebarSelectStrategy}
            params={sidebarParams}
            setParams={sidebarSetParams}
            runBacktest={canRun ? runBacktest : () => {}}
            loading={loading}
            error={error}
            autoUpdate={autoUpdate && backtestMode === 'single'}
            setAutoUpdate={setAutoUpdate}
            autoUpdateLoading={autoUpdateLoading}
            hasResult={hasResult}
            resultIsStale={resultIsStale}
            backtestMode={backtestMode}
            setBacktestMode={setBacktestMode}
            activeSlot={activeSlot}
            setActiveSlot={setActiveSlot}
            buildMultiPreset={backtestMode !== 'single' ? buildMultiPreset : undefined}
            currentMetrics={backtestMode === 'single' ? (filteredResult?.metrics ?? null) : (filteredMultiResult?.metrics ?? null)}
          />

          <Dashboard
            filteredResult={backtestMode === 'single' ? filteredResult : null}
            multiResult={backtestMode !== 'single' ? filteredMultiResult : null}
            backtestMode={backtestMode}
            selectedSessions={selectedSessions}
            onSessionsChange={setSelectedSessions}
            dataSource="Local"
            initialEquity={initialEquity}
            autoUpdate={autoUpdate && backtestMode === 'single'}
            autoUpdateLoading={autoUpdateLoading}
            previousMetrics={previousMetrics}
          />
        </div>
      )}

      {/* Data Management Mode */}
      {mode === 'data' && <MarketDataPanel />}

      {/* Favorites Mode */}
      {mode === 'favorites' && (
        <FavoritesPage
          onLoadPreset={handleLoadFavoritePreset}
          multiContext={isMulti ? {
            backtestMode,
            activeSlot,
            slotLabel: (backtestMode === 'multi_asset' ? ['Asset 1', 'Asset 2'] : ['Strategy 1', 'Strategy 2'])[activeSlot],
            lockedSymbol: backtestMode === 'multi_strat' ? selectedSymbol : undefined,
            otherSlotSymbol: backtestMode === 'multi_asset'
              ? (activeSlot === 0 ? selectedSymbol2 : selectedSymbol)
              : undefined,
          } : undefined}
        />
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
