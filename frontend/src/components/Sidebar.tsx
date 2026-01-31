import { Database, ShieldAlert, Settings, Play } from 'lucide-react';
import { type Strategy, type Contract } from '../api';

// Type for strategy parameters
type StrategyParamValue = number | string | boolean;
type StrategyParams = Record<string, StrategyParamValue>;

interface SidebarProps {
    // Data State
    dataSource: string;
    setDataSource: (v: string) => void;
    ticker: string;
    setTicker: (v: string) => void;
    contracts: Contract[];
    selectedContract: Contract | null;
    setSelectedContract: (c: Contract) => void;
    interval: string;
    setInterval: (v: string) => void;
    days: number;
    setDays: (v: number) => void;
    startDate: string;
    setStartDate: (v: string) => void;
    endDate: string;
    setEndDate: (v: string) => void;
    topstepLiveMode: boolean;
    setTopstepLiveMode: (v: boolean) => void;
    manualContractId: string;
    setManualContractId: (v: string) => void;

    // Risk State
    initialEquity: number;
    setInitialEquity: (v: number) => void;
    riskPerTrade: number;
    setRiskPerTrade: (v: number) => void;

    // Trade Filters
    maxContracts: number;
    setMaxContracts: (v: number) => void;
    blockMarketOpen: boolean;
    setBlockMarketOpen: (v: boolean) => void;

    // Strategy State
    strategies: Strategy[];
    selectedStrategy: Strategy | null;
    selectStrategy: (s: Strategy) => void;
    params: StrategyParams;
    setParams: (fn: (prev: StrategyParams) => StrategyParams) => void;

    // Actions
    runBacktest: () => void;
    loading: boolean;
    error: string;
}

export function Sidebar({
    dataSource, setDataSource,
    ticker, setTicker,
    contracts, selectedContract, setSelectedContract,
    interval, setInterval,
    // days, setDays, // Removed unused props
    startDate, setStartDate,
    endDate, setEndDate,
    topstepLiveMode, setTopstepLiveMode,
    manualContractId, setManualContractId,
    initialEquity, setInitialEquity,
    riskPerTrade, setRiskPerTrade,
    maxContracts, setMaxContracts,
    blockMarketOpen, setBlockMarketOpen,
    strategies, selectedStrategy, selectStrategy,
    params, setParams,
    runBacktest, loading, error
}: SidebarProps) {

    const handleParamChange = (key: string, value: StrategyParamValue) => {
        setParams(prev => ({ ...prev, [key]: value }));
    };

    return (
        <div className="space-y-6">

            {/* 1. Data Source */}
            <div className="glass-panel rounded-xl p-5">
                <div className="flex items-center gap-2 mb-4 text-blue-400 font-semibold">
                    <Database className="w-5 h-5" />
                    <h2>Data Source</h2>
                </div>

                <div className="flex bg-gray-900/50 rounded-lg p-1 mb-4 border border-gray-700">
                    {['Yahoo', 'Topstep'].map(src => (
                        <button
                            key={src}
                            onClick={() => setDataSource(src)}
                            className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-all ${dataSource === src
                                ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20'
                                : 'text-gray-400 hover:text-white hover:bg-white/5'
                                }`}
                        >
                            {src}
                        </button>
                    ))}
                </div>

                <div className="space-y-4">
                    {dataSource === 'Yahoo' && (
                        <div>
                            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">Ticker</label>
                            <input
                                type="text"
                                className="input-base"
                                value={ticker}
                                onChange={e => setTicker(e.target.value)}
                            />
                        </div>
                    )}
                    {dataSource === 'Topstep' && (
                        <div>
                            <div className="flex gap-2 mb-2 p-1 bg-gray-900/40 rounded-lg">
                                <button
                                    onClick={() => setTopstepLiveMode(true)}
                                    className={`flex-1 text-xs py-1 rounded ${topstepLiveMode ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
                                >
                                    Active Contract
                                </button>
                                <button
                                    onClick={() => setTopstepLiveMode(false)}
                                    className={`flex-1 text-xs py-1 rounded ${!topstepLiveMode ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
                                >
                                    Legacy/Manual
                                </button>
                            </div>

                            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">
                                {topstepLiveMode ? "Active Contract" : "Contract ID"}
                            </label>

                            {topstepLiveMode ? (
                                <select
                                    className="input-base appearance-none"
                                    value={selectedContract?.id || ''}
                                    onChange={(e) => {
                                        const c = contracts.find(c => c.id === e.target.value);
                                        if (c) setSelectedContract(c);
                                    }}
                                >
                                    {contracts.length === 0 && <option>Loading...</option>}
                                    {contracts.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                                </select>
                            ) : (
                                <input
                                    type="text"
                                    className="input-base"
                                    placeholder="e.g. CON.F.US.ES.Z23 (Contract ID)"
                                    value={manualContractId}
                                    onChange={e => setManualContractId(e.target.value)}
                                />
                            )}
                        </div>
                    )}

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">Timeframe</label>
                            <select
                                className="input-base"
                                value={interval}
                                onChange={e => setInterval(e.target.value)}
                            >
                                {['1m', '2m', '5m', '15m', '30m', '1h', '4h', '1d'].map(t => <option key={t} value={t}>{t}</option>)}
                            </select>
                        </div>
                        {/* Display Duration Helper */}

                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">Start Date</label>
                            <input
                                type="date"
                                className="input-base"
                                value={startDate}
                                onChange={e => setStartDate(e.target.value)}
                            />
                        </div>
                        <div>
                            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">End Date</label>
                            <input
                                type="date"
                                className="input-base"
                                value={endDate}
                                onChange={e => setEndDate(e.target.value)}
                            />
                        </div>
                    </div>
                    {startDate && endDate && (
                        <div className="text-xs text-center text-gray-500 -mt-2">
                            Duration: {Math.max(0, Math.ceil((new Date(endDate).getTime() - new Date(startDate).getTime()) / (1000 * 60 * 60 * 24))) + 1} days
                        </div>
                    )}
                </div>
            </div>

            {/* 2. Risk Management */}
            <div className="glass-panel rounded-xl p-5">
                <div className="flex items-center gap-2 mb-4 text-emerald-400 font-semibold">
                    <ShieldAlert className="w-5 h-5" />
                    <h2>Risk Management</h2>
                </div>
                <div className="grid grid-cols-2 gap-3">
                    <div>
                        <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">Capital ($)</label>
                        <input
                            type="number"
                            className="input-base"
                            value={initialEquity}
                            onChange={e => setInitialEquity(Number(e.target.value))}
                        />
                    </div>
                    <div>
                        <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">Risk %</label>
                        <input
                            type="number"
                            className="input-base"
                            value={riskPerTrade}
                            step="0.1"
                            onChange={e => setRiskPerTrade(Number(e.target.value))}
                        />
                    </div>
                </div>

                {/* Trade Filters */}
                <div className="mt-4 pt-4 border-t border-gray-700/50">
                    <label className="block text-xs text-gray-500 mb-3 uppercase tracking-wider font-medium">Trade Filters</label>
                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="block text-xs text-gray-400 mb-1">Max Contracts</label>
                            <input
                                type="number"
                                className="input-base"
                                value={maxContracts}
                                min={1}
                                max={1000}
                                onChange={e => setMaxContracts(Number(e.target.value))}
                            />
                        </div>
                        <div className="flex items-end">
                            <label className="flex items-center space-x-2 cursor-pointer group h-[38px]">
                                <input
                                    type="checkbox"
                                    checked={blockMarketOpen}
                                    onChange={() => setBlockMarketOpen(!blockMarketOpen)}
                                    className="sr-only peer"
                                />
                                <div className="w-5 h-5 border-2 border-gray-600 rounded bg-gray-900 group-hover:border-gray-500 peer-checked:bg-emerald-600 peer-checked:border-emerald-600 transition-all flex items-center justify-center">
                                    {blockMarketOpen && (
                                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                        </svg>
                                    )}
                                </div>
                                <span className="text-gray-400 text-xs">Block Open</span>
                            </label>
                        </div>
                    </div>
                    {blockMarketOpen && (
                        <p className="text-xs text-gray-600 mt-2">
                            Blocks first 5 min of sessions
                        </p>
                    )}
                </div>
            </div>

            {/* 3. Strategy Params */}
            {selectedStrategy && (
                <div className="glass-panel rounded-xl p-5">
                    <div className="flex items-center gap-2 mb-4 text-purple-400 font-semibold">
                        <Settings className="w-5 h-5" />
                        <h2>Parameters</h2>
                    </div>

                    <div className="mb-4">
                        <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">Strategy</label>
                        <select
                            className="input-base"
                            value={selectedStrategy?.name || ''}
                            onChange={(e) => {
                                const s = strategies.find(s => s.name === e.target.value);
                                if (s) selectStrategy(s);
                            }}
                        >
                            {strategies.map(s => <option key={s.name} value={s.name}>{s.name}</option>)}
                        </select>
                    </div>

                    <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                        {Object.entries(params)
                            .filter(([key]) => key !== 'tick_size') // Hide tick_size
                            .map(([key, value]) => (
                                <div key={key}>
                                    <label className="block text-xs text-gray-500 mb-1 uppercase tracking-wider font-medium">{key.replace(/_/g, ' ')}</label>
                                    {typeof value === 'boolean' ? (
                                        <select
                                            className="input-base focus:border-purple-500 focus:ring-purple-500"
                                            value={value ? 'true' : 'false'}
                                            onChange={e => handleParamChange(key, e.target.value === 'true')}
                                        >
                                            <option value="true">True</option>
                                            <option value="false">False</option>
                                        </select>
                                    ) : (
                                        <input
                                            type={typeof value === 'number' ? 'number' : 'text'}
                                            className="input-base focus:border-purple-500 focus:ring-purple-500"
                                            value={value}
                                            step={typeof value === 'number' && !Number.isInteger(value) ? "0.1" : "1"}
                                            onChange={e => handleParamChange(key, typeof value === 'number' ? Number(e.target.value) : e.target.value)}
                                        />
                                    )}
                                </div>
                            ))}
                    </div>
                </div>
            )}

            <button
                onClick={runBacktest}
                disabled={loading}
                className={`w-full py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2 transform transition-all ${loading
                    ? 'bg-gray-700 cursor-not-allowed text-gray-500'
                    : 'btn-primary'
                    }`}
            >
                {loading ? (
                    <span className="flex items-center gap-2">
                        <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Processing...
                    </span>
                ) : (
                    <>
                        <Play className="w-5 h-5 fill-current" />
                        Run Backtest
                    </>
                )}
            </button>

            {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-200 text-sm break-words flex gap-3">
                    <ShieldAlert className="w-5 h-5 shrink-0 text-red-400" />
                    <span>{error}</span>
                </div>
            )}
        </div>
    );
}
