import { useState, useEffect, useMemo, type Dispatch, type SetStateAction } from 'react';
import { Clock3, Database, Lock, Play, RefreshCw, Settings, ShieldAlert, Star, ChevronDown, ChevronUp, Trash2, RotateCcw } from 'lucide-react';
import {
    type AvailableDataset,
    type BacktestEngineSettings,
    type BacktestPreset,
    type Strategy,
    loadPresets,
    loadPresetsLocal,
    savePreset,
    deletePreset as deletePresetFromStorage,
} from '../api';

type StrategyParamValue = number | string | boolean;
type StrategyParams = Record<string, StrategyParamValue>;

interface SidebarProps {
    availableData: AvailableDataset[];
    selectedSymbol: string;
    setSelectedSymbol: (v: string) => void;
    interval: string;
    setInterval: (v: string) => void;
    startDatetime: string;
    setStartDatetime: (v: string) => void;
    endDatetime: string;
    setEndDatetime: (v: string) => void;
    initialEquity: number;
    setInitialEquity: (v: number) => void;
    riskPerTrade: number;
    setRiskPerTrade: (v: number) => void;
    maxContracts: number;
    setMaxContracts: (v: number) => void;
    engineSettings: BacktestEngineSettings;
    setEngineSettings: Dispatch<SetStateAction<BacktestEngineSettings>>;
    strategies: Strategy[];
    selectedStrategy: Strategy | null;
    selectStrategy: (s: Strategy) => void;
    params: StrategyParams;
    setParams: Dispatch<SetStateAction<StrategyParams>>;
    runBacktest: () => void;
    loading: boolean;
    error: string;
    autoUpdate: boolean;
    setAutoUpdate: (v: boolean) => void;
    autoUpdateLoading: boolean;
    hasResult: boolean;
}

function formatParamLabel(key: string): string {
    return key.replace(/_/g, ' ');
}

function toClockValue(hour: number, minute: number): string {
    return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
}

function parseClockValue(value: string): { hour: number; minute: number } | null {
    const [hourStr, minuteStr] = value.split(':');
    const hour = Number(hourStr);
    const minute = Number(minuteStr);
    if (!Number.isFinite(hour) || !Number.isFinite(minute)) {
        return null;
    }
    return { hour, minute };
}

export function Sidebar({
    availableData,
    selectedSymbol,
    setSelectedSymbol,
    interval,
    setInterval,
    startDatetime,
    setStartDatetime,
    endDatetime,
    setEndDatetime,
    initialEquity,
    setInitialEquity,
    riskPerTrade,
    setRiskPerTrade,
    maxContracts,
    setMaxContracts,
    engineSettings,
    setEngineSettings,
    strategies,
    selectedStrategy,
    selectStrategy,
    params,
    setParams,
    runBacktest,
    loading,
    error,
    autoUpdate,
    setAutoUpdate,
    autoUpdateLoading,
    hasResult,
}: SidebarProps) {
    // Favorites state — load from localStorage instantly, then refresh from backend
    const [presets, setPresets] = useState<BacktestPreset[]>(() => loadPresetsLocal());
    const [favoritesOpen, setFavoritesOpen] = useState(false);
    const [saveConfirm, setSaveConfirm] = useState(false);

    useEffect(() => {
        loadPresets().then(setPresets);
    }, []);

    const selectedDataset = useMemo(() => {
        return availableData.find((dataset) => dataset.symbol === selectedSymbol) || null;
    }, [availableData, selectedSymbol]);

    const availableTimeframes = useMemo(() => {
        return selectedDataset?.timeframes || [];
    }, [selectedDataset]);

    const minStartDatetime = useMemo(() => {
        if (!selectedDataset || !selectedStrategy) return '';
        const minStarts = selectedDataset.min_start_per_strategy[selectedStrategy.name];
        if (minStarts && minStarts[interval]) {
            return minStarts[interval].slice(0, 16);
        }
        return selectedDataset.start_date.slice(0, 16);
    }, [selectedDataset, selectedStrategy, interval]);

    const maxEndDatetime = useMemo(() => {
        if (!selectedDataset) return '';
        return selectedDataset.end_date.slice(0, 16);
    }, [selectedDataset]);

    const visibleParams = useMemo(() => {
        return Object.entries(params).filter(([key]) => key !== 'tick_size');
    }, [params]);

    const handleParamChange = (key: string, value: StrategyParamValue) => {
        setParams((prev) => ({ ...prev, [key]: value }));
    };

    const handleBlackoutUpdate = (
        index: number,
        updates: Partial<BacktestEngineSettings['blackout_windows'][number]>,
    ) => {
        setEngineSettings((prev) => ({
            ...prev,
            blackout_windows: prev.blackout_windows.map((window, windowIndex) => (
                windowIndex === index ? { ...window, ...updates } : window
            )),
        }));
    };

    // --- Favorites handlers ---

    const handleSavePreset = async () => {
        if (!selectedStrategy) return;
        const preset: BacktestPreset = {
            id: crypto.randomUUID(),
            name: `${selectedStrategy.name} - ${selectedSymbol} ${interval}`,
            createdAt: new Date().toISOString(),
            symbol: selectedSymbol,
            interval,
            startDatetime,
            endDatetime,
            initialEquity,
            riskPerTrade,
            maxContracts,
            strategyName: selectedStrategy.name,
            params: { ...params },
            engineSettings: JSON.parse(JSON.stringify(engineSettings)),
        };
        const updated = await savePreset(preset);
        setPresets(updated);
        setSaveConfirm(true);
        setTimeout(() => setSaveConfirm(false), 2000);
    };

    const handleDeletePreset = async (id: string) => {
        const updated = await deletePresetFromStorage(id);
        setPresets(updated);
    };

    const handleLoadPreset = (preset: BacktestPreset) => {
        // Strategy
        const strategy = strategies.find((s) => s.name === preset.strategyName);
        if (strategy) {
            selectStrategy(strategy);
            // Override params after selectStrategy resets to defaults
            setTimeout(() => setParams(({ ...preset.params })), 0);
        }
        // Data
        setSelectedSymbol(preset.symbol);
        setInterval(preset.interval);
        setStartDatetime(preset.startDatetime);
        setEndDatetime(preset.endDatetime);
        // Risk
        setInitialEquity(preset.initialEquity);
        setRiskPerTrade(preset.riskPerTrade);
        setMaxContracts(preset.maxContracts);
        // Engine
        setEngineSettings(JSON.parse(JSON.stringify(preset.engineSettings)));

        setFavoritesOpen(false);
    };

    const renderParamInput = (key: string, value: StrategyParamValue) => {
        if (typeof value === 'boolean') {
            return (
                <select
                    className="input-base"
                    value={value ? 'true' : 'false'}
                    onChange={(event) => handleParamChange(key, event.target.value === 'true')}
                >
                    <option value="true">True</option>
                    <option value="false">False</option>
                </select>
            );
        }

        if (key === 'signal_type') {
            return (
                <select
                    className="input-base"
                    value={String(value)}
                    onChange={(event) => handleParamChange(key, event.target.value)}
                >
                    <option value="SMA">SMA</option>
                    <option value="EMA">EMA</option>
                </select>
            );
        }

        if (key === 'filter_method') {
            return (
                <select
                    className="input-base"
                    value={String(value)}
                    onChange={(event) => handleParamChange(key, event.target.value)}
                >
                    <option value="slope">slope</option>
                    <option value="spread">spread</option>
                </select>
            );
        }

        if (typeof value === 'string') {
            return (
                <input
                    type="text"
                    className="input-base"
                    value={value}
                    onChange={(event) => handleParamChange(key, event.target.value)}
                />
            );
        }

        return (
            <input
                type="number"
                className="input-base"
                value={value}
                step={!Number.isInteger(value) ? '0.1' : '1'}
                onChange={(event) => handleParamChange(key, Number(event.target.value))}
            />
        );
    };

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <div className={`glass-panel rounded-xl p-5 ${autoUpdate ? 'opacity-60' : ''}`}>
                    <div className="flex items-center gap-2 mb-4 text-blue-400 font-semibold">
                        <Database className="w-5 h-5" />
                        <h2>Data</h2>
                        {autoUpdate && <Lock className="w-3.5 h-3.5 text-gray-500" />}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">Symbol</label>
                            <select
                                className="input-base"
                                disabled={autoUpdate}
                                value={selectedSymbol}
                                onChange={(event) => {
                                    setSelectedSymbol(event.target.value);
                                    const nextDataset = availableData.find((dataset) => dataset.symbol === event.target.value);
                                    if (nextDataset && !nextDataset.timeframes.includes(interval)) {
                                        setInterval(nextDataset.timeframes[nextDataset.timeframes.length - 1] || '5m');
                                    }
                                }}
                            >
                                {availableData.length === 0 && <option>Loading...</option>}
                                {availableData.map((dataset) => (
                                    <option key={dataset.symbol} value={dataset.symbol}>
                                        {dataset.symbol}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div>
                            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">Timeframe</label>
                            <select
                                className="input-base"
                                disabled={autoUpdate}
                                value={interval}
                                onChange={(event) => setInterval(event.target.value)}
                            >
                                {availableTimeframes.map((timeframe) => (
                                    <option key={timeframe} value={timeframe}>
                                        {timeframe}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div>
                            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">Start Date & Time</label>
                            <input
                                type="datetime-local"
                                className="input-base"
                                disabled={autoUpdate}
                                value={startDatetime}
                                min={minStartDatetime}
                                max={endDatetime || maxEndDatetime}
                                onChange={(event) => setStartDatetime(event.target.value)}
                            />
                            {minStartDatetime && (
                                <p className="text-xs text-gray-600 mt-1">
                                    Min: {minStartDatetime.replace('T', ' ')} (warmup indicateurs)
                                </p>
                            )}
                        </div>

                        <div>
                            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">End Date & Time</label>
                            <input
                                type="datetime-local"
                                className="input-base"
                                disabled={autoUpdate}
                                value={endDatetime}
                                min={startDatetime || minStartDatetime}
                                max={maxEndDatetime}
                                onChange={(event) => setEndDatetime(event.target.value)}
                            />
                        </div>
                    </div>

                    {startDatetime && endDatetime && (
                        <div className="mt-4 text-xs text-gray-500">
                            Duration: {Math.max(0, Math.ceil((new Date(endDatetime).getTime() - new Date(startDatetime).getTime()) / (1000 * 60 * 60 * 24)))} days
                        </div>
                    )}

                </div>

                <div className="glass-panel rounded-xl p-5">
                    <div className="flex items-center gap-2 mb-4 text-emerald-400 font-semibold">
                        <ShieldAlert className="w-5 h-5" />
                        <h2>Risk</h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">Capital ($)</label>
                            <input
                                type="number"
                                className="input-base"
                                value={initialEquity}
                                onChange={(event) => setInitialEquity(Number(event.target.value))}
                            />
                        </div>

                        <div>
                            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">Risk %</label>
                            <input
                                type="number"
                                className="input-base"
                                value={riskPerTrade}
                                step="0.1"
                                onChange={(event) => setRiskPerTrade(Number(event.target.value))}
                            />
                        </div>

                        <div>
                            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">Max Contracts</label>
                            <input
                                type="number"
                                className="input-base"
                                min={1}
                                max={1000}
                                value={maxContracts}
                                onChange={(event) => setMaxContracts(Number(event.target.value))}
                            />
                        </div>

                        <div>
                            <label className="flex items-center gap-2 text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={engineSettings.daily_win_limit_enabled}
                                    onChange={(event) => setEngineSettings((prev) => ({
                                        ...prev,
                                        daily_win_limit_enabled: event.target.checked,
                                    }))}
                                    className="rounded border-gray-600 bg-gray-900 text-emerald-500 focus:ring-emerald-500"
                                />
                                Max Daily Win ($)
                            </label>
                            <input
                                type="number"
                                className="input-base"
                                min={0}
                                step={50}
                                value={engineSettings.daily_win_limit}
                                disabled={!engineSettings.daily_win_limit_enabled}
                                onChange={(event) => setEngineSettings((prev) => ({
                                    ...prev,
                                    daily_win_limit: Number(event.target.value),
                                }))}
                            />
                        </div>

                        <div>
                            <label className="flex items-center gap-2 text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={engineSettings.daily_loss_limit_enabled}
                                    onChange={(event) => setEngineSettings((prev) => ({
                                        ...prev,
                                        daily_loss_limit_enabled: event.target.checked,
                                    }))}
                                    className="rounded border-gray-600 bg-gray-900 text-red-500 focus:ring-red-500"
                                />
                                Max Daily Loss ($)
                            </label>
                            <input
                                type="number"
                                className="input-base"
                                min={0}
                                step={50}
                                value={engineSettings.daily_loss_limit}
                                disabled={!engineSettings.daily_loss_limit_enabled}
                                onChange={(event) => setEngineSettings((prev) => ({
                                    ...prev,
                                    daily_loss_limit: Number(event.target.value),
                                }))}
                            />
                        </div>
                    </div>
                </div>

            </div>

            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
                <div className="glass-panel rounded-xl p-5 xl:col-span-7">
                    <div className="flex items-center gap-2 mb-4 text-purple-400 font-semibold">
                        <Settings className="w-5 h-5" />
                        <h2>Strategy Parameters</h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-4">
                        <div className={autoUpdate ? 'opacity-60' : ''}>
                            <label className="block text-xs text-gray-500 mb-1 uppercase tracking-wider font-medium">
                                Strategy {autoUpdate && <Lock className="w-3 h-3 inline text-gray-600 ml-1" />}
                            </label>
                            <select
                                className="input-base"
                                disabled={autoUpdate}
                                value={selectedStrategy?.name || ''}
                                onChange={(event) => {
                                    const strategy = strategies.find((item) => item.name === event.target.value);
                                    if (strategy) {
                                        selectStrategy(strategy);
                                    }
                                }}
                            >
                                {strategies.map((strategy) => (
                                    <option key={strategy.name} value={strategy.name}>
                                        {strategy.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                        {visibleParams.map(([key, value]) => (
                            <div key={key}>
                                <label className="block text-xs text-gray-500 mb-1 uppercase tracking-wider font-medium">
                                    {formatParamLabel(key)}
                                </label>
                                {renderParamInput(key, value)}
                            </div>
                        ))}
                    </div>
                </div>

                <div className={`glass-panel rounded-xl p-5 ${selectedStrategy ? 'xl:col-span-5' : 'xl:col-span-12'}`}>
                    <div className="flex items-center gap-2 mb-4 text-cyan-400 font-semibold">
                        <Clock3 className="w-5 h-5" />
                        <h2>Engine</h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">Auto-Close Enabled</label>
                            <select
                                className="input-base"
                                value={engineSettings.auto_close_enabled ? 'true' : 'false'}
                                onChange={(event) => setEngineSettings((prev) => ({
                                    ...prev,
                                    auto_close_enabled: event.target.value === 'true',
                                }))}
                            >
                                <option value="true">True</option>
                                <option value="false">False</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">Auto-Close Time</label>
                            <input
                                type="time"
                                className="input-base"
                                value={toClockValue(engineSettings.auto_close_hour, engineSettings.auto_close_minute)}
                                onChange={(event) => {
                                    const parsed = parseClockValue(event.target.value);
                                    if (!parsed) return;
                                    setEngineSettings((prev) => ({
                                        ...prev,
                                        auto_close_hour: parsed.hour,
                                        auto_close_minute: parsed.minute,
                                    }));
                                }}
                            />
                        </div>

                        <div className={`md:col-span-2 ${autoUpdate ? 'opacity-60' : ''}`}>
                            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider font-medium">
                                Debug Export {autoUpdate && <Lock className="w-3 h-3 inline text-gray-600 ml-1" />}
                            </label>
                            <select
                                className="input-base"
                                disabled={autoUpdate}
                                value={engineSettings.debug ? 'true' : 'false'}
                                onChange={(event) => setEngineSettings((prev) => ({
                                    ...prev,
                                    debug: event.target.value === 'true',
                                }))}
                            >
                                <option value="false">False</option>
                                <option value="true">True</option>
                            </select>
                            <p className="text-xs text-gray-600 mt-1">
                                Export CSV bar-par-bar avec les indicateurs et les événements de trade.
                            </p>
                        </div>
                    </div>

                    <div className="mt-5 pt-5 border-t border-gray-700/50">
                        <h3 className="text-xs text-gray-400 uppercase tracking-wider font-semibold mb-3">Blackout Windows</h3>
                        <div className="grid grid-cols-1 gap-3">
                            {engineSettings.blackout_windows.map((window, index) => (
                                <div key={index} className="rounded-lg border border-gray-700/40 bg-gray-900/20 p-3">
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
                                        <div>
                                            <label className="block text-xs text-gray-500 mb-1 uppercase tracking-wider font-medium">
                                                Window {index + 1}
                                            </label>
                                            <select
                                                className="input-base"
                                                value={window.active ? 'true' : 'false'}
                                                onChange={(event) => handleBlackoutUpdate(index, { active: event.target.value === 'true' })}
                                            >
                                                <option value="false">Disabled</option>
                                                <option value="true">Enabled</option>
                                            </select>
                                        </div>

                                        <div>
                                            <label className="block text-xs text-gray-500 mb-1 uppercase tracking-wider font-medium">Start</label>
                                            <input
                                                type="time"
                                                className="input-base"
                                                value={toClockValue(window.start_hour, window.start_minute)}
                                                onChange={(event) => {
                                                    const parsed = parseClockValue(event.target.value);
                                                    if (!parsed) return;
                                                    handleBlackoutUpdate(index, {
                                                        start_hour: parsed.hour,
                                                        start_minute: parsed.minute,
                                                    });
                                                }}
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-xs text-gray-500 mb-1 uppercase tracking-wider font-medium">End</label>
                                            <input
                                                type="time"
                                                className="input-base"
                                                value={toClockValue(window.end_hour, window.end_minute)}
                                                onChange={(event) => {
                                                    const parsed = parseClockValue(event.target.value);
                                                    if (!parsed) return;
                                                    handleBlackoutUpdate(index, {
                                                        end_hour: parsed.hour,
                                                        end_minute: parsed.minute,
                                                    });
                                                }}
                                            />
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Favorites panel */}
            {presets.length > 0 && (
                <div className="glass-panel rounded-xl overflow-hidden">
                    <button
                        onClick={() => setFavoritesOpen(!favoritesOpen)}
                        className="w-full flex items-center justify-between px-5 py-3 text-sm font-medium text-amber-400 hover:bg-gray-800/30 transition-colors"
                    >
                        <span className="flex items-center gap-2">
                            <Star className="w-4 h-4 fill-amber-400" />
                            Favorites ({presets.length})
                        </span>
                        {favoritesOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>

                    {favoritesOpen && (
                        <div className="border-t border-gray-700/50 max-h-64 overflow-y-auto">
                            {presets.map((preset) => (
                                <div
                                    key={preset.id}
                                    className="flex items-center justify-between px-5 py-3 border-b border-gray-800/50 last:border-b-0 hover:bg-gray-800/20 transition-colors group"
                                >
                                    <div className="min-w-0 flex-1">
                                        <div className="text-sm text-gray-200 font-medium truncate">{preset.name}</div>
                                        <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-3 flex-wrap">
                                            <span>${preset.initialEquity.toLocaleString()} / {preset.riskPerTrade}%</span>
                                            <span>{preset.startDatetime.replace('T', ' ')} - {preset.endDatetime.replace('T', ' ')}</span>
                                            <span className="text-gray-600">{new Date(preset.createdAt).toLocaleDateString()}</span>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-1 ml-3 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button
                                            onClick={() => handleLoadPreset(preset)}
                                            className="p-1.5 rounded-md text-blue-400 hover:bg-blue-500/10 transition-colors"
                                            title="Load preset"
                                        >
                                            <RotateCcw className="w-3.5 h-3.5" />
                                        </button>
                                        <button
                                            onClick={() => handleDeletePreset(preset.id)}
                                            className="p-1.5 rounded-md text-red-400 hover:bg-red-500/10 transition-colors"
                                            title="Delete preset"
                                        >
                                            <Trash2 className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Action buttons */}
            <div className="flex gap-3">
                {!autoUpdate && (
                    <button
                        onClick={runBacktest}
                        disabled={loading}
                        className={`flex-1 py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2 transition-all ${
                            loading ? 'bg-gray-700 cursor-not-allowed text-gray-500' : 'btn-primary'
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
                )}

                {autoUpdate && (
                    <div className="flex-1 py-4 rounded-xl font-medium text-sm flex items-center justify-center gap-2 bg-emerald-600/15 border border-emerald-500/30 text-emerald-300">
                        {autoUpdateLoading ? (
                            <>
                                <RefreshCw className="w-4 h-4 animate-spin" />
                                Updating...
                            </>
                        ) : (
                            <>
                                <RefreshCw className="w-4 h-4" />
                                Auto-Update Active
                            </>
                        )}
                    </div>
                )}

                <button
                    onClick={() => {
                        if (!autoUpdate && !hasResult) return;
                        setAutoUpdate(!autoUpdate);
                    }}
                    disabled={!hasResult && !autoUpdate}
                    className={`group px-5 py-4 rounded-xl font-medium transition-all flex items-center gap-2 ${
                        autoUpdate
                            ? 'bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 hover:bg-red-500/10 hover:border-red-500/40 hover:text-red-300'
                            : hasResult
                                ? 'bg-gray-800/60 border border-gray-700 text-gray-400 hover:text-emerald-400 hover:border-emerald-500/40 hover:bg-emerald-500/10'
                                : 'bg-gray-800/30 border border-gray-800 text-gray-600 cursor-not-allowed'
                    }`}
                    title={autoUpdate ? 'Disable auto-update' : hasResult ? 'Enable auto-update' : 'Run a backtest first to enable auto-update'}
                >
                    <RefreshCw className={`w-5 h-5 transition-colors ${autoUpdate ? 'text-emerald-400 group-hover:text-red-300' : ''}`} />
                    {autoUpdate ? 'Stop' : 'Auto'}
                </button>

                <button
                    onClick={handleSavePreset}
                    disabled={!selectedStrategy}
                    className={`px-5 py-4 rounded-xl font-medium transition-all flex items-center gap-2 ${
                        saveConfirm
                            ? 'bg-amber-500/20 border border-amber-500/40 text-amber-300'
                            : 'bg-gray-800/60 border border-gray-700 text-gray-400 hover:text-amber-400 hover:border-amber-500/40 hover:bg-amber-500/10'
                    }`}
                    title="Save current parameters as favorite"
                >
                    <Star className={`w-5 h-5 ${saveConfirm ? 'fill-amber-400 text-amber-400' : ''}`} />
                    {saveConfirm ? 'Saved!' : 'Save'}
                </button>
            </div>

            {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-200 text-sm break-words flex gap-3">
                    <ShieldAlert className="w-5 h-5 shrink-0 text-red-400" />
                    <span>{error}</span>
                </div>
            )}
        </div>
    );
}
