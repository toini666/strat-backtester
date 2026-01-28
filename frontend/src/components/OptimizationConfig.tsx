import { useState, useEffect, useCallback } from 'react';
import { Settings, AlertTriangle, Play, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { api, type Strategy, type Contract, type ParamRangeInfo, type ParameterRangeInput } from '../api';

interface ParamConfig {
    name: string;
    enabled: boolean;
    min: number;
    max: number;
    step: number;
    paramType: 'float' | 'int' | 'bool';
    defaultValue: number | boolean;
    count: number;
}

interface OptimizationConfigProps {
    strategies: Strategy[];
    contracts: Contract[];
    onRunOptimization: (config: {
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
    }) => void;
    loading: boolean;
}

export function OptimizationConfig({
    strategies,
    contracts,
    onRunOptimization,
    loading
}: OptimizationConfigProps) {
    // Strategy selection
    const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
    const [paramConfigs, setParamConfigs] = useState<ParamConfig[]>([]);
    const [loadingParams, setLoadingParams] = useState(false);

    // Data config
    const [dataSource, setDataSource] = useState<'Yahoo' | 'Topstep'>('Topstep');
    const [ticker, setTicker] = useState('BTC-USD');
    const [selectedContract, setSelectedContract] = useState<Contract | null>(null);
    const [interval, setInterval] = useState('15m');
    const [days, setDays] = useState(14);

    // Risk config
    const [initialEquity, setInitialEquity] = useState(50000);
    const [riskPerTrade, setRiskPerTrade] = useState(1.0);

    // Sessions
    const [selectedSessions, setSelectedSessions] = useState<string[]>(['Asia', 'UK', 'US']);

    // UI state
    const [expandedParams, setExpandedParams] = useState(true);

    // Load param ranges when strategy changes
    useEffect(() => {
        if (!selectedStrategy) {
            setParamConfigs([]);
            return;
        }

        setLoadingParams(true);
        api.getStrategyParamRanges(selectedStrategy.name)
            .then(data => {
                const configs: ParamConfig[] = data.param_ranges.map(p => {
                    if (p.param_type === 'bool') {
                        return {
                            name: p.name,
                            enabled: false,
                            min: 0,
                            max: 1,
                            step: 1,
                            paramType: 'bool',
                            defaultValue: p.default,
                            count: 2
                        };
                    }

                    const values = p.values as number[];
                    const minVal = Math.min(...values);
                    const maxVal = Math.max(...values);
                    const step = values.length > 1 ? values[1] - values[0] : 1;

                    return {
                        name: p.name,
                        enabled: false,
                        min: minVal,
                        max: maxVal,
                        step: Math.abs(step),
                        paramType: p.param_type,
                        defaultValue: p.default,
                        count: p.count
                    };
                });
                setParamConfigs(configs);
            })
            .catch(err => {
                console.error('Failed to load param ranges:', err);
                setParamConfigs([]);
            })
            .finally(() => setLoadingParams(false));
    }, [selectedStrategy]);

    // Set default contract when contracts load
    useEffect(() => {
        if (contracts.length > 0 && !selectedContract) {
            setSelectedContract(contracts[0]);
        }
    }, [contracts, selectedContract]);

    // Set default strategy when strategies load
    useEffect(() => {
        if (strategies.length > 0 && !selectedStrategy) {
            setSelectedStrategy(strategies[0]);
        }
    }, [strategies, selectedStrategy]);

    // Calculate counts
    const calculateParamCount = useCallback((config: ParamConfig): number => {
        if (!config.enabled) return 1;
        if (config.paramType === 'bool') return 2;

        const range = config.max - config.min;
        if (config.step <= 0) return 1;
        return Math.floor(range / config.step) + 1;
    }, []);

    const paramCombinations = paramConfigs.reduce((acc, p) => acc * calculateParamCount(p), 1);
    const sessionCombinations = Math.pow(2, selectedSessions.length) - 1;
    const totalCombinations = paramCombinations * Math.max(1, sessionCombinations);

    const toggleParam = useCallback((name: string) => {
        setParamConfigs(prev => prev.map(p =>
            p.name === name ? { ...p, enabled: !p.enabled } : p
        ));
    }, []);

    const updateParamConfig = useCallback((name: string, field: 'min' | 'max' | 'step', value: number) => {
        setParamConfigs(prev => prev.map(p =>
            p.name === name ? { ...p, [field]: value } : p
        ));
    }, []);

    const toggleSession = useCallback((session: string) => {
        setSelectedSessions(prev =>
            prev.includes(session)
                ? prev.filter(s => s !== session)
                : [...prev, session]
        );
    }, []);

    const handleRun = useCallback(() => {
        if (!selectedStrategy) return;

        const enabledParams: ParameterRangeInput[] = paramConfigs
            .filter(p => p.enabled)
            .map(p => ({
                name: p.name,
                min_value: p.min,
                max_value: p.max,
                step: p.step,
                param_type: p.paramType
            }));

        onRunOptimization({
            strategyName: selectedStrategy.name,
            ticker,
            source: dataSource,
            contractId: selectedContract?.id || null,
            interval,
            days,
            parameters: enabledParams,
            sessions: selectedSessions,
            initialEquity,
            riskPerTrade: riskPerTrade / 100
        });
    }, [selectedStrategy, paramConfigs, ticker, dataSource, selectedContract, interval, days, selectedSessions, initialEquity, riskPerTrade, onRunOptimization]);

    const canRun = selectedStrategy &&
        selectedSessions.length > 0 &&
        paramConfigs.some(p => p.enabled) &&
        totalCombinations <= 5000;

    return (
        <div className="glass-panel rounded-xl p-6 space-y-6">
            <div className="flex items-center gap-3 border-b border-gray-700/50 pb-4">
                <div className="p-2 bg-purple-600/20 rounded-lg">
                    <Settings className="w-5 h-5 text-purple-400" />
                </div>
                <h2 className="text-lg font-semibold text-gray-200">Parameter Optimization</h2>
            </div>

            {/* Strategy Selection */}
            <div className="space-y-3">
                <label className="text-sm text-gray-400 font-medium">Strategy</label>
                <select
                    value={selectedStrategy?.name || ''}
                    onChange={(e) => {
                        const strat = strategies.find(s => s.name === e.target.value);
                        setSelectedStrategy(strat || null);
                    }}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-gray-200 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-colors"
                >
                    {strategies.map(s => (
                        <option key={s.name} value={s.name}>{s.name}</option>
                    ))}
                </select>
            </div>

            {/* Data Source */}
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <label className="text-sm text-gray-400 font-medium">Data Source</label>
                    <select
                        value={dataSource}
                        onChange={(e) => setDataSource(e.target.value as 'Yahoo' | 'Topstep')}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-200 text-sm"
                    >
                        <option value="Topstep">Topstep</option>
                        <option value="Yahoo">Yahoo Finance</option>
                    </select>
                </div>

                {dataSource === 'Topstep' ? (
                    <div className="space-y-2">
                        <label className="text-sm text-gray-400 font-medium">Contract</label>
                        <select
                            value={selectedContract?.id || ''}
                            onChange={(e) => {
                                const contract = contracts.find(c => c.id === e.target.value);
                                setSelectedContract(contract || null);
                            }}
                            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-200 text-sm"
                        >
                            {contracts.map(c => (
                                <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                        </select>
                    </div>
                ) : (
                    <div className="space-y-2">
                        <label className="text-sm text-gray-400 font-medium">Ticker</label>
                        <input
                            type="text"
                            value={ticker}
                            onChange={(e) => setTicker(e.target.value)}
                            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-200 text-sm"
                        />
                    </div>
                )}
            </div>

            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <label className="text-sm text-gray-400 font-medium">Timeframe</label>
                    <select
                        value={interval}
                        onChange={(e) => setInterval(e.target.value)}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-200 text-sm"
                    >
                        {['1m', '2m', '5m', '15m', '30m', '1h', '4h', '1d'].map(tf => (
                            <option key={tf} value={tf}>{tf}</option>
                        ))}
                    </select>
                </div>
                <div className="space-y-2">
                    <label className="text-sm text-gray-400 font-medium">Days</label>
                    <input
                        type="number"
                        value={days}
                        onChange={(e) => setDays(parseInt(e.target.value) || 14)}
                        min={1}
                        max={365}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-200 text-sm"
                    />
                </div>
            </div>

            {/* Risk Management */}
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <label className="text-sm text-gray-400 font-medium">Initial Equity</label>
                    <input
                        type="number"
                        value={initialEquity}
                        onChange={(e) => setInitialEquity(parseInt(e.target.value) || 50000)}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-200 text-sm"
                    />
                </div>
                <div className="space-y-2">
                    <label className="text-sm text-gray-400 font-medium">Risk Per Trade (%)</label>
                    <input
                        type="number"
                        value={riskPerTrade}
                        onChange={(e) => setRiskPerTrade(parseFloat(e.target.value) || 1)}
                        step={0.1}
                        min={0.1}
                        max={10}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-200 text-sm"
                    />
                </div>
            </div>

            {/* Sessions Selection */}
            <div className="space-y-3">
                <label className="text-sm text-gray-400 font-medium">Sessions to Test</label>
                <div className="flex gap-4">
                    {['Asia', 'UK', 'US'].map(session => (
                        <label key={session} className="flex items-center space-x-2 cursor-pointer group">
                            <input
                                type="checkbox"
                                checked={selectedSessions.includes(session)}
                                onChange={() => toggleSession(session)}
                                className="sr-only peer"
                            />
                            <div className="w-5 h-5 border-2 border-gray-600 rounded bg-gray-900 group-hover:border-gray-500 peer-checked:bg-purple-600 peer-checked:border-purple-600 transition-all flex items-center justify-center">
                                {selectedSessions.includes(session) && (
                                    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                    </svg>
                                )}
                            </div>
                            <span className="text-gray-300 text-sm font-medium">{session}</span>
                        </label>
                    ))}
                </div>
                <p className="text-xs text-gray-500">
                    Session combinations: <span className="text-purple-400 font-mono">{sessionCombinations}</span>
                </p>
            </div>

            {/* Parameters to Optimize */}
            <div className="space-y-3">
                <button
                    onClick={() => setExpandedParams(!expandedParams)}
                    className="w-full flex items-center justify-between text-sm text-gray-400 font-medium hover:text-gray-300 transition-colors"
                >
                    <span>Parameters to Optimize</span>
                    {expandedParams ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>

                {expandedParams && (
                    <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
                        {loadingParams ? (
                            <div className="flex items-center justify-center py-8 text-gray-500">
                                <Loader2 className="w-5 h-5 animate-spin mr-2" />
                                Loading parameters...
                            </div>
                        ) : paramConfigs.length === 0 ? (
                            <p className="text-sm text-gray-500 py-4 text-center">
                                No parameters available for optimization
                            </p>
                        ) : (
                            paramConfigs.map(param => (
                                <div
                                    key={param.name}
                                    className={`p-3 rounded-lg border transition-all ${
                                        param.enabled
                                            ? 'bg-purple-900/20 border-purple-700/50'
                                            : 'bg-gray-800/50 border-gray-700/30'
                                    }`}
                                >
                                    <label className="flex items-center justify-between cursor-pointer mb-2">
                                        <div className="flex items-center space-x-2">
                                            <input
                                                type="checkbox"
                                                checked={param.enabled}
                                                onChange={() => toggleParam(param.name)}
                                                className="sr-only peer"
                                            />
                                            <div className="w-4 h-4 border-2 border-gray-600 rounded bg-gray-900 peer-checked:bg-purple-600 peer-checked:border-purple-600 transition-all flex items-center justify-center">
                                                {param.enabled && (
                                                    <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                                    </svg>
                                                )}
                                            </div>
                                            <span className="text-gray-300 text-sm font-mono">{param.name}</span>
                                        </div>
                                        <span className="text-xs text-gray-500 font-mono">
                                            {calculateParamCount(param)} values
                                        </span>
                                    </label>

                                    {param.enabled && param.paramType !== 'bool' && (
                                        <div className="grid grid-cols-3 gap-2 mt-2">
                                            <div>
                                                <label className="text-xs text-gray-500">Min</label>
                                                <input
                                                    type="number"
                                                    value={param.min}
                                                    onChange={(e) => updateParamConfig(param.name, 'min', parseFloat(e.target.value))}
                                                    step={param.paramType === 'int' ? 1 : 0.1}
                                                    className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-200 text-sm font-mono"
                                                />
                                            </div>
                                            <div>
                                                <label className="text-xs text-gray-500">Max</label>
                                                <input
                                                    type="number"
                                                    value={param.max}
                                                    onChange={(e) => updateParamConfig(param.name, 'max', parseFloat(e.target.value))}
                                                    step={param.paramType === 'int' ? 1 : 0.1}
                                                    className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-200 text-sm font-mono"
                                                />
                                            </div>
                                            <div>
                                                <label className="text-xs text-gray-500">Step</label>
                                                <input
                                                    type="number"
                                                    value={param.step}
                                                    onChange={(e) => updateParamConfig(param.name, 'step', parseFloat(e.target.value))}
                                                    step={param.paramType === 'int' ? 1 : 0.1}
                                                    min={0.001}
                                                    className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-200 text-sm font-mono"
                                                />
                                            </div>
                                        </div>
                                    )}

                                    {param.enabled && param.paramType === 'bool' && (
                                        <p className="text-xs text-gray-500 mt-1">
                                            Will test: True, False
                                        </p>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                )}

                <p className="text-xs text-gray-500">
                    Parameter combinations: <span className="text-purple-400 font-mono">{paramCombinations}</span>
                </p>
            </div>

            {/* Summary */}
            <div className={`p-4 rounded-lg border ${
                totalCombinations > 1000
                    ? totalCombinations > 5000
                        ? 'bg-red-900/20 border-red-700/50'
                        : 'bg-yellow-900/20 border-yellow-700/50'
                    : 'bg-gray-800/50 border-gray-700/30'
            }`}>
                <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Total Backtests</span>
                    <span className={`text-2xl font-bold font-mono ${
                        totalCombinations > 5000 ? 'text-red-400' :
                        totalCombinations > 1000 ? 'text-yellow-400' : 'text-purple-400'
                    }`}>
                        {totalCombinations.toLocaleString()}
                    </span>
                </div>

                {totalCombinations > 1000 && (
                    <div className="flex items-center gap-2 mt-2 text-xs">
                        <AlertTriangle className={`w-4 h-4 ${totalCombinations > 5000 ? 'text-red-400' : 'text-yellow-400'}`} />
                        <span className={totalCombinations > 5000 ? 'text-red-400' : 'text-yellow-400'}>
                            {totalCombinations > 5000
                                ? 'Too many combinations. Maximum is 5000.'
                                : 'This may take a while to complete.'}
                        </span>
                    </div>
                )}
            </div>

            {/* Run Button */}
            <button
                onClick={handleRun}
                disabled={!canRun || loading}
                className={`w-full py-3 px-4 rounded-lg font-semibold flex items-center justify-center gap-2 transition-all ${
                    canRun && !loading
                        ? 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg shadow-purple-900/30'
                        : 'bg-gray-800 text-gray-500 cursor-not-allowed'
                }`}
            >
                {loading ? (
                    <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Running Optimization...
                    </>
                ) : (
                    <>
                        <Play className="w-5 h-5" />
                        Run Optimization
                    </>
                )}
            </button>

            {!canRun && !loading && (
                <p className="text-xs text-center text-gray-500">
                    {!paramConfigs.some(p => p.enabled) && 'Select at least one parameter to optimize'}
                    {selectedSessions.length === 0 && 'Select at least one session'}
                    {totalCombinations > 5000 && 'Reduce combinations to 5000 or less'}
                </p>
            )}
        </div>
    );
}
