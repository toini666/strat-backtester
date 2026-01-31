import { useState, useEffect, useCallback, useRef } from 'react';
import { Settings, AlertTriangle, Play, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { api, type Strategy, type Contract, type ParameterRangeInput } from '../api';

interface ParamConfig {
    name: string;
    enabled: boolean;
    min: number;
    max: number;
    step: number;
    paramType: 'float' | 'int' | 'bool';
    defaultValue: number | boolean;
    customValue: number | boolean;
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
        maxContracts: number;
        blockMarketOpen: boolean;
        startDate?: string;
        endDate?: string;
        topstepLiveMode?: boolean;
    }) => void;
    loading: boolean;
    onContractsNeeded?: () => void;
    initialConfig?: {
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
    } | null;
}

export function OptimizationConfig({
    strategies,
    contracts,
    onRunOptimization,
    loading,
    onContractsNeeded,
    initialConfig
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
    const [startDate, setStartDate] = useState(() => {
        const d = new Date();
        d.setDate(d.getDate() - 30); // 30 days before end date
        return d.toISOString().split('T')[0];
    });
    const [endDate, setEndDate] = useState(() => {
        const d = new Date();
        d.setDate(d.getDate() - 1);
        return d.toISOString().split('T')[0];
    });
    const [topstepLiveMode, setTopstepLiveMode] = useState(true);
    const [manualContractId, setManualContractId] = useState('');

    // Risk config
    const [initialEquity, setInitialEquity] = useState(50000);
    const [riskPerTrade, setRiskPerTrade] = useState(1.0);

    // Trade filters
    const [maxContracts, setMaxContracts] = useState(50);
    const [blockMarketOpen, setBlockMarketOpen] = useState(true);

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
                const configs: ParamConfig[] = data.param_ranges
                    .filter(p => p.name !== 'tick_size') // Hide tick_size
                    .map(p => {
                        if (p.param_type === 'bool') {
                            return {
                                name: p.name,
                                enabled: false,
                                min: 0,
                                max: 1,
                                step: 1,
                                paramType: 'bool',
                                defaultValue: p.default,
                                customValue: p.default,
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
                            customValue: p.default,
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

    // Fetch contracts when Topstep is selected and contracts are empty
    useEffect(() => {
        if (dataSource === 'Topstep' && contracts.length === 0 && onContractsNeeded) {
            onContractsNeeded();
        }
    }, [dataSource, contracts.length, onContractsNeeded]);

    // Set default contract when contracts load
    useEffect(() => {
        if (contracts.length > 0 && !selectedContract) {
            setSelectedContract(contracts[0]);
        }
    }, [contracts, selectedContract]);

    // Set default strategy when strategies load OR from initialConfig
    useEffect(() => {
        if (strategies.length > 0) {
            if (initialConfig) {
                const strat = strategies.find(s => s.name === initialConfig.strategyName);
                if (strat) setSelectedStrategy(strat);
            } else if (!selectedStrategy) {
                setSelectedStrategy(strategies[0]);
            }
        }
    }, [strategies, initialConfig]);

    // Apply initial config when available
    // Use a ref to track if we've already applied this specific config instance
    const configAppliedRef = useRef<object | null>(null);

    useEffect(() => {
        if (initialConfig && selectedStrategy && selectedStrategy.name === initialConfig.strategyName && paramConfigs.length > 0) {
            // Only apply if this specific config object hasn't been applied yet
            if (configAppliedRef.current === initialConfig) return;

            configAppliedRef.current = initialConfig;

            // Check if paramConfigs match the current strategy (basic check)
            const hasMatchingParams = paramConfigs.some(p => initialConfig.parameters.some(ip => ip.name === p.name));
            if (!hasMatchingParams) return;

            setTicker(initialConfig.ticker);
            setDataSource(initialConfig.source);
            if (initialConfig.contractId) {
                const contract = contracts.find(c => c.id === initialConfig.contractId);
                if (contract) setSelectedContract(contract);
            }
            setInterval(initialConfig.interval);
            setDays(initialConfig.days);
            if (initialConfig.startDate) setStartDate(initialConfig.startDate);
            if (initialConfig.endDate) setEndDate(initialConfig.endDate);
            if (initialConfig.topstepLiveMode !== undefined) setTopstepLiveMode(initialConfig.topstepLiveMode);

            // Handle Manual Contract if Legacy mode was saved
            if (initialConfig.source === 'Topstep' && !initialConfig.topstepLiveMode && initialConfig.contractId) {
                setManualContractId(initialConfig.contractId);
            }

            setInitialEquity(initialConfig.initialEquity);

            // Fix Risk Per Trade: If < 1, assumes it was saved as decimal (e.g. 0.01). Convert to %.
            // If >= 1, assumes legacy or already %. Use as is.
            // However, backend saves exactly what was sent.
            // App.tsx sends 0.01 default.
            // If saved as 0.01, we want 1.0 displayed. => * 100.
            // If saved as 1.0 (legacy), we want 1.0 displayed. => * 1?
            // Safer logic: users input 0.1 to 10.
            const savedRisk = initialConfig.riskPerTrade;
            if (savedRisk < 0.1) {
                setRiskPerTrade(savedRisk * 100);
            } else {
                setRiskPerTrade(savedRisk);
            }

            setMaxContracts(initialConfig.maxContracts);
            setBlockMarketOpen(initialConfig.blockMarketOpen);
            setSelectedSessions(initialConfig.sessions);

            // Map parameters
            setParamConfigs(prev => prev.map(p => {
                const storedParam = initialConfig.parameters.find(sp => sp.name === p.name);
                if (storedParam) {
                    if (storedParam.min_value !== storedParam.max_value) {
                        // Only update if different to avoid infinite loops if it triggers re-render
                        if (p.enabled && p.min === storedParam.min_value && p.max === storedParam.max_value && p.step === storedParam.step) return p;

                        return {
                            ...p,
                            enabled: true,
                            min: storedParam.min_value,
                            max: storedParam.max_value,
                            step: storedParam.step
                        };
                    } else {
                        // Fixed value
                        const val = storedParam.param_type === 'bool' ? Boolean(storedParam.min_value) : storedParam.min_value;
                        if (!p.enabled && p.customValue === val) return p;

                        return {
                            ...p,
                            enabled: false,
                            customValue: val
                        };
                    }
                }
                return p;
            }));
        }
    }, [initialConfig, selectedStrategy, contracts, paramConfigs]);

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

    const updateParamConfig = useCallback((name: string, field: 'min' | 'max' | 'step' | 'customValue', value: number | boolean) => {
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

        const parameters: ParameterRangeInput[] = paramConfigs.map(p => {
            if (p.enabled) {
                // Optimization Enabled: Send Range
                return {
                    name: p.name,
                    min_value: p.min,
                    max_value: p.max,
                    step: p.step,
                    param_type: p.paramType
                };
            } else {
                // Optimization Disabled: Send Fixed Value as Range [Val, Val]
                return {
                    name: p.name,
                    min_value: Number(p.customValue),
                    max_value: Number(p.customValue),
                    step: 1, // Dummy step to ensure loop runs once
                    param_type: p.paramType
                };
            }
        });

        onRunOptimization({
            strategyName: selectedStrategy.name,
            ticker,
            source: dataSource,
            contractId: topstepLiveMode ? (selectedContract?.id || null) : manualContractId,
            interval,
            days,
            parameters,
            sessions: selectedSessions,
            initialEquity,
            riskPerTrade: riskPerTrade / 100,
            maxContracts,
            blockMarketOpen,
            startDate,
            endDate,
            topstepLiveMode
        });
    }, [selectedStrategy, paramConfigs, ticker, dataSource, selectedContract, manualContractId, interval, days, selectedSessions, initialEquity, riskPerTrade, maxContracts, blockMarketOpen, startDate, endDate, topstepLiveMode, onRunOptimization]);

    const canRun = selectedStrategy &&
        selectedSessions.length > 0 &&
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
                        <div className="flex justify-between items-center">
                            <label className="text-sm text-gray-400 font-medium">{topstepLiveMode ? "Active Contract" : "Contract ID"}</label>
                            <div className="flex gap-1 bg-gray-900/40 rounded p-0.5">
                                <button
                                    onClick={() => setTopstepLiveMode(true)}
                                    className={`text-[10px] px-2 py-0.5 rounded ${topstepLiveMode ? 'bg-purple-600 text-white' : 'text-gray-500 hover:text-white'}`}
                                >
                                    Active
                                </button>
                                <button
                                    onClick={() => setTopstepLiveMode(false)}
                                    className={`text-[10px] px-2 py-0.5 rounded ${!topstepLiveMode ? 'bg-purple-600 text-white' : 'text-gray-500 hover:text-white'}`}
                                >
                                    Legacy
                                </button>
                            </div>
                        </div>

                        {topstepLiveMode ? (
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
                        ) : (
                            <input
                                type="text"
                                placeholder="e.g. ESZ3"
                                value={manualContractId}
                                onChange={(e) => setManualContractId(e.target.value)}
                                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-200 text-sm"
                            />
                        )}
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
                    <div className="flex justify-between items-center">
                        <label className="text-sm text-gray-400 font-medium">Date Range</label>
                        {startDate && endDate && (
                            <span className="text-[10px] text-gray-500 font-mono">
                                {Math.max(0, Math.ceil((new Date(endDate).getTime() - new Date(startDate).getTime()) / (1000 * 60 * 60 * 24))) + 1} days
                            </span>
                        )}
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        <input
                            type="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-2 text-gray-200 text-xs"
                        />
                        <input
                            type="date"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-2 text-gray-200 text-xs"
                        />
                    </div>
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

            {/* Trade Filters */}
            <div className="space-y-3">
                <label className="text-sm text-gray-400 font-medium">Trade Filters</label>
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <label className="text-xs text-gray-500">Max Contracts/Position</label>
                        <input
                            type="number"
                            value={maxContracts}
                            onChange={(e) => setMaxContracts(parseInt(e.target.value) || 50)}
                            min={1}
                            max={1000}
                            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-200 text-sm"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-xs text-gray-500">Block Market Open</label>
                        <label className="flex items-center space-x-2 cursor-pointer group h-[38px]">
                            <input
                                type="checkbox"
                                checked={blockMarketOpen}
                                onChange={() => setBlockMarketOpen(!blockMarketOpen)}
                                className="sr-only peer"
                            />
                            <div className="w-5 h-5 border-2 border-gray-600 rounded bg-gray-900 group-hover:border-gray-500 peer-checked:bg-purple-600 peer-checked:border-purple-600 transition-all flex items-center justify-center">
                                {blockMarketOpen && (
                                    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                    </svg>
                                )}
                            </div>
                            <span className="text-gray-300 text-sm">First 5 min of sessions</span>
                        </label>
                    </div>
                </div>
                <p className="text-xs text-gray-500">
                    {blockMarketOpen && 'Blocks: 0h00-0h05, 9h00-9h05, 15h30-15h35 (Paris time)'}
                </p>
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
                    <span>Parameters</span>
                    {expandedParams ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>

                {expandedParams && (
                    <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
                        {loadingParams ? (
                            <div className="flex items-center justify-center py-8 text-gray-500">
                                <Loader2 className="w-5 h-5 animate-spin mr-2" />
                                Loading parameters...
                            </div>
                        ) : paramConfigs.length === 0 ? (
                            <p className="text-sm text-gray-500 py-4 text-center">
                                No parameters available
                            </p>
                        ) : (
                            <>
                                <>
                                    {/* Unified Parameter List */}
                                    <div className="space-y-4">
                                        <div className="flex items-center justify-between text-xs text-gray-500 uppercase font-semibold border-b border-gray-800 pb-2">
                                            <span>Parameter</span>
                                            <div className="flex gap-8 mr-4">
                                                <span>Mode</span>
                                                <span>Values</span>
                                            </div>
                                        </div>

                                        {paramConfigs.map(param => (
                                            <div
                                                key={param.name}
                                                className={`p-3 rounded-lg border transition-all ${param.enabled
                                                    ? 'bg-purple-900/20 border-purple-700/50'
                                                    : 'bg-gray-800/30 border-gray-700/30'
                                                    }`}
                                            >
                                                <div className="flex flex-col gap-3">
                                                    {/* Header Row: Name + Toggle + Count */}
                                                    <div className="flex items-center justify-between">
                                                        <div className="flex items-center gap-3">
                                                            <label className="flex items-center space-x-2 cursor-pointer group">
                                                                <input
                                                                    type="checkbox"
                                                                    checked={param.enabled}
                                                                    onChange={() => toggleParam(param.name)}
                                                                    className="sr-only peer"
                                                                />
                                                                <div className={`w-10 h-5 rounded-full p-1 transition-all ${param.enabled ? 'bg-purple-600' : 'bg-gray-700'}`}>
                                                                    <div className={`w-3 h-3 bg-white rounded-full shadow-sm transform transition-transform ${param.enabled ? 'translate-x-5' : 'translate-x-0'}`} />
                                                                </div>
                                                            </label>
                                                            <span className={`text-sm font-mono font-medium ${param.enabled ? 'text-purple-300' : 'text-gray-400'}`}>
                                                                {param.name}
                                                            </span>
                                                        </div>

                                                        <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${param.enabled ? 'bg-purple-900/50 text-purple-300' : 'bg-gray-800 text-gray-500'}`}>
                                                            {calculateParamCount(param)} {calculateParamCount(param) === 1 ? 'value' : 'values'}
                                                        </span>
                                                    </div>

                                                    {/* Content Row: Range Inputs OR Fixed Input */}
                                                    <div className="pl-14">
                                                        {param.enabled ? (
                                                            /* Optimization Mode (Range) */
                                                            param.paramType === 'bool' ? (
                                                                <div className="text-xs text-purple-400 italic">
                                                                    Will test both True and False
                                                                </div>
                                                            ) : (
                                                                <div className="grid grid-cols-3 gap-3">
                                                                    <div>
                                                                        <label className="block text-[10px] text-gray-500 mb-1 uppercase">Min</label>
                                                                        <input
                                                                            type="number"
                                                                            value={param.min}
                                                                            onChange={(e) => updateParamConfig(param.name, 'min', parseFloat(e.target.value))}
                                                                            step={param.paramType === 'int' ? 1 : 0.01}
                                                                            className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-gray-200 text-sm font-mono focus:border-purple-500 focus:ring-1 focus:ring-purple-500"
                                                                        />
                                                                    </div>
                                                                    <div>
                                                                        <label className="block text-[10px] text-gray-500 mb-1 uppercase">Max</label>
                                                                        <input
                                                                            type="number"
                                                                            value={param.max}
                                                                            onChange={(e) => updateParamConfig(param.name, 'max', parseFloat(e.target.value))}
                                                                            step={param.paramType === 'int' ? 1 : 0.01}
                                                                            className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-gray-200 text-sm font-mono focus:border-purple-500 focus:ring-1 focus:ring-purple-500"
                                                                        />
                                                                    </div>
                                                                    <div>
                                                                        <label className="block text-[10px] text-gray-500 mb-1 uppercase">Step</label>
                                                                        <input
                                                                            type="number"
                                                                            value={param.step}
                                                                            onChange={(e) => updateParamConfig(param.name, 'step', parseFloat(e.target.value))}
                                                                            step={param.paramType === 'int' ? 1 : 0.001}
                                                                            min={0.001}
                                                                            className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-gray-200 text-sm font-mono focus:border-purple-500 focus:ring-1 focus:ring-purple-500"
                                                                        />
                                                                    </div>
                                                                </div>
                                                            )
                                                        ) : (
                                                            /* Fixed Value Mode */
                                                            <div className="flex items-center gap-4">
                                                                <label className="text-[10px] text-gray-500 uppercase whitespace-nowrap">Fixed Value:</label>
                                                                {param.paramType === 'bool' ? (
                                                                    <div className="flex items-center bg-gray-900 rounded-lg border border-gray-700 p-1">
                                                                        <button
                                                                            onClick={() => updateParamConfig(param.name, 'customValue', true)}
                                                                            className={`px-3 py-1 text-xs rounded-md transition-all ${param.customValue === true ? 'bg-gray-700 text-white shadow-sm' : 'text-gray-500 hover:text-gray-300'}`}
                                                                        >
                                                                            True
                                                                        </button>
                                                                        <button
                                                                            onClick={() => updateParamConfig(param.name, 'customValue', false)}
                                                                            className={`px-3 py-1 text-xs rounded-md transition-all ${param.customValue === false ? 'bg-gray-700 text-white shadow-sm' : 'text-gray-500 hover:text-gray-300'}`}
                                                                        >
                                                                            False
                                                                        </button>
                                                                    </div>
                                                                ) : (
                                                                    <input
                                                                        type="number"
                                                                        value={Number(param.customValue)}
                                                                        onChange={(e) => updateParamConfig(param.name, 'customValue', parseFloat(e.target.value))}
                                                                        step={param.paramType === 'int' ? 1 : 0.01}
                                                                        className="w-32 bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-gray-200 text-sm font-mono focus:border-gray-500 focus:ring-1 focus:ring-gray-500"
                                                                    />
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </>
                            </>
                        )}
                    </div>
                )}

                <p className="text-xs text-gray-500">
                    Parameter combinations: <span className="text-purple-400 font-mono">{paramCombinations}</span>
                </p>
            </div>

            {/* Summary */}
            <div className={`p-4 rounded-lg border ${totalCombinations > 1000
                ? totalCombinations > 5000
                    ? 'bg-red-900/20 border-red-700/50'
                    : 'bg-yellow-900/20 border-yellow-700/50'
                : 'bg-gray-800/50 border-gray-700/30'
                }`}>
                <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Total Backtests</span>
                    <span className={`text-2xl font-bold font-mono ${totalCombinations > 5000 ? 'text-red-400' :
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
                className={`w-full py-3 px-4 rounded-lg font-semibold flex items-center justify-center gap-2 transition-all ${canRun && !loading
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

            {/* Loading Progress Indicator */}
            {loading && (
                <div className="p-4 rounded-lg bg-purple-900/20 border border-purple-700/30 space-y-3">
                    <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-400">Testing combinations...</span>
                        <span className="text-purple-400 font-mono">{totalCombinations.toLocaleString()}</span>
                    </div>
                    <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-purple-600 to-indigo-600 rounded-full animate-pulse" style={{ width: '100%' }} />
                    </div>
                    <p className="text-xs text-gray-500 text-center">
                        This may take a few minutes depending on the number of combinations
                    </p>
                </div>
            )}

            {!canRun && !loading && (
                <p className="text-xs text-center text-gray-500">
                    {/* {!paramConfigs.some(p => p.enabled) && 'Select at least one parameter to optimize'} -- Removed check to allow running with ALL fixed params */}
                    {selectedSessions.length === 0 && 'Select at least one session'}
                    {totalCombinations > 5000 && 'Reduce combinations to 5000 or less'}
                </p>
            )}
        </div>
    );
}
