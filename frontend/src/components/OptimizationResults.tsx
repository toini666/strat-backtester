import { useState } from 'react';
import { Trophy, TrendingUp, Activity, Hash, TrendingDown, ArrowLeft, Play, ChevronDown, ChevronUp } from 'lucide-react';
import { type OptimizationResultItem } from '../api';

interface OptimizationConfigSummary {
    ticker: string;
    source: string;
    contractId: string | null;
    interval: string;
    days: number;
    initialEquity: number;
    riskPerTrade: number;
    maxContracts: number;
    blockMarketOpen: boolean;
}

interface OptimizationResultsProps {
    results: OptimizationResultItem[];
    strategyName: string;
    totalCombinations: number;
    completed: number;
    errors: number;
    config?: OptimizationConfigSummary; // Make optional to avoid immediate breakage if parent not updated
    onSelectResult: (result: OptimizationResultItem) => void;
    onBack: () => void;
}

export function OptimizationResults({
    results,
    strategyName,
    totalCombinations,
    completed,
    errors,
    config,
    onSelectResult,
    onBack
}: OptimizationResultsProps) {
    const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

    const toggleRow = (index: number) => {
        const newExpanded = new Set(expandedRows);
        if (newExpanded.has(index)) {
            newExpanded.delete(index);
        } else {
            // Optional: Close others if we want strict accordion (one at a time)
            // newExpanded.clear(); 
            newExpanded.add(index);
        }
        setExpandedRows(newExpanded);
    };

    const handleRunBacktest = (result: OptimizationResultItem) => {
        onSelectResult(result);
    };

    return (
        <div className="space-y-6 animate-fadeIn">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <button
                        onClick={onBack}
                        className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors"
                    >
                        <ArrowLeft className="w-5 h-5 text-gray-400" />
                    </button>
                    <div>
                        <h2 className="text-xl font-bold text-gray-200 flex items-center gap-2">
                            <Trophy className="w-6 h-6 text-yellow-400" />
                            Optimization Results
                        </h2>
                        <p className="text-sm text-gray-500 mt-1">
                            {strategyName} • {completed.toLocaleString()} / {totalCombinations.toLocaleString()} combinations
                            {errors > 0 && <span className="text-red-400"> • {errors} errors</span>}
                        </p>
                    </div>
                </div>
            </div>

            {/* Configuration Summary */}
            {config && (
                <div className="glass-panel rounded-xl p-4 border border-gray-700/50 bg-gray-800/30">
                    <h3 className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-3">Optimization Configuration</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 text-sm">
                        <div>
                            <span className="text-gray-500 block text-xs">Strategy</span>
                            <span className="text-gray-200 font-medium">{strategyName}</span>
                        </div>
                        <div>
                            <span className="text-gray-500 block text-xs">Source</span>
                            <span className="text-gray-200 font-medium">{config.source}</span>
                        </div>
                        {config.source === 'Topstep' ? (
                            <div className="col-span-2">
                                <span className="text-gray-500 block text-xs">Contract</span>
                                <span className="text-gray-200 font-medium">{config.contractId || 'N/A'}</span>
                            </div>
                        ) : (
                            <div>
                                <span className="text-gray-500 block text-xs">Ticker</span>
                                <span className="text-gray-200 font-medium">{config.ticker}</span>
                            </div>
                        )}
                        <div>
                            <span className="text-gray-500 block text-xs">Timeframe</span>
                            <span className="text-gray-200 font-medium">{config.interval}</span>
                        </div>
                        <div>
                            <span className="text-gray-500 block text-xs">Days</span>
                            <span className="text-gray-200 font-medium">{config.days}</span>
                        </div>
                        <div>
                            <span className="text-gray-500 block text-xs">Initial Equity</span>
                            <span className="text-gray-200 font-medium">${config.initialEquity.toLocaleString()}</span>
                        </div>
                        <div>
                            <span className="text-gray-500 block text-xs">Risk Per Trade</span>
                            <span className="text-gray-200 font-medium">{config.riskPerTrade * 100}%</span>
                        </div>
                        <div>
                            <span className="text-gray-500 block text-xs">Max Contracts</span>
                            <span className="text-gray-200 font-medium">{config.maxContracts}</span>
                        </div>
                        <div>
                            <span className="text-gray-500 block text-xs">Block Open</span>
                            <span className="text-gray-200 font-medium">{config.blockMarketOpen ? 'Yes' : 'No'}</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Summary Stats */}
            <div className="grid grid-cols-4 gap-4">
                <div className="glass-panel rounded-xl p-4">
                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Best Return</div>
                    <div className={`text-2xl font-bold font-mono ${results[0]?.total_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {results[0]?.total_return >= 0 ? '+' : ''}{results[0]?.total_return.toFixed(2)}%
                    </div>
                </div>
                <div className="glass-panel rounded-xl p-4">
                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Best Win Rate</div>
                    <div className="text-2xl font-bold font-mono text-blue-400">
                        {Math.max(...results.map(r => r.win_rate)).toFixed(1)}%
                    </div>
                </div>
                <div className="glass-panel rounded-xl p-4">
                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Most Trades</div>
                    <div className="text-2xl font-bold font-mono text-orange-400">
                        {Math.max(...results.map(r => r.trade_count))}
                    </div>
                </div>
                <div className="glass-panel rounded-xl p-4">
                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Best Max DD</div>
                    <div className="text-2xl font-bold font-mono text-purple-400">
                        {Math.max(...results.map(r => r.max_drawdown)).toFixed(2)}%
                    </div>
                </div>
            </div>

            {/* Results Table */}
            <div className="glass-panel rounded-xl overflow-hidden">
                <div className="p-4 border-b border-gray-700/50 bg-gray-800/30">
                    <h3 className="text-gray-400 text-sm uppercase tracking-wider font-semibold">
                        Top 20 Results (sorted by Total Return)
                    </h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead className="bg-gray-900/50 text-gray-400">
                            <tr>
                                <th className="px-4 py-3 text-left font-medium w-10"></th>
                                <th className="px-4 py-3 text-left font-medium">#</th>
                                <th className="px-4 py-3 text-right font-medium">
                                    <div className="flex items-center justify-end gap-1">
                                        <TrendingUp className="w-4 h-4" />
                                        Return
                                    </div>
                                </th>
                                <th className="px-4 py-3 text-right font-medium">
                                    <div className="flex items-center justify-end gap-1">
                                        <Activity className="w-4 h-4" />
                                        Win Rate
                                    </div>
                                </th>
                                <th className="px-4 py-3 text-right font-medium">
                                    <div className="flex items-center justify-end gap-1">
                                        <Hash className="w-4 h-4" />
                                        Trades
                                    </div>
                                </th>
                                <th className="px-4 py-3 text-right font-medium">
                                    <div className="flex items-center justify-end gap-1">
                                        <TrendingDown className="w-4 h-4" />
                                        Max DD
                                    </div>
                                </th>
                                <th className="px-4 py-3 text-left font-medium">Sessions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700/30">
                            {results.map((result, index) => (
                                <>
                                    <tr
                                        key={index}
                                        onClick={() => toggleRow(index)}
                                        className={`cursor-pointer transition-colors ${expandedRows.has(index)
                                            ? 'bg-blue-900/20'
                                            : 'hover:bg-white/5'
                                            }`}
                                    >
                                        <td className="px-4 py-3 text-gray-500">
                                            {expandedRows.has(index) ? (
                                                <ChevronUp className="w-4 h-4" />
                                            ) : (
                                                <ChevronDown className="w-4 h-4" />
                                            )}
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${result.rank === 1 ? 'bg-yellow-500/20 text-yellow-400' :
                                                result.rank === 2 ? 'bg-gray-400/20 text-gray-300' :
                                                    result.rank === 3 ? 'bg-orange-500/20 text-orange-400' :
                                                        'bg-gray-800 text-gray-500'
                                                }`}>
                                                {result.rank}
                                            </span>
                                        </td>
                                        <td className={`px-4 py-3 text-right font-mono font-bold ${result.total_return >= 0 ? 'text-green-400' : 'text-red-400'
                                            }`}>
                                            {result.total_return >= 0 ? '+' : ''}{result.total_return.toFixed(2)}%
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-blue-400">
                                            {result.win_rate.toFixed(1)}%
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-orange-400">
                                            {result.trade_count}
                                        </td>
                                        <td className={`px-4 py-3 text-right font-mono ${result.max_drawdown > -5 ? 'text-green-400' :
                                            result.max_drawdown > -15 ? 'text-yellow-400' : 'text-red-400'
                                            }`}>
                                            {result.max_drawdown.toFixed(2)}%
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="flex gap-1 flex-wrap">
                                                {result.sessions.map(sess => (
                                                    <span
                                                        key={sess}
                                                        className={`px-2 py-0.5 text-xs rounded-full font-medium ${sess === 'Asia' ? 'bg-pink-500/20 text-pink-400' :
                                                            sess === 'UK' ? 'bg-blue-500/20 text-blue-400' :
                                                                'bg-green-500/20 text-green-400'
                                                            }`}
                                                    >
                                                        {sess}
                                                    </span>
                                                ))}
                                            </div>
                                        </td>
                                    </tr>
                                    {expandedRows.has(index) && (
                                        <tr className="bg-gray-900/40">
                                            <td colSpan={7} className="px-4 py-4">
                                                <div className="flex flex-col md:flex-row gap-6 animate-fadeIn">
                                                    <div className="flex-1">
                                                        <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-2 font-semibold">Parameters</h4>
                                                        <div className="grid grid-cols-2 lg:grid-cols-3 gap-x-4 gap-y-2 bg-gray-800/50 p-3 rounded-lg border border-gray-700/50">
                                                            {Object.entries(result.parameters).map(([key, value]) => (
                                                                <div key={key} className="flex justify-between items-center text-sm">
                                                                    <span className="text-gray-400 mr-2 break-all">{key.replace('rsi_', 'RSI ')}:</span>
                                                                    <span className="text-gray-200 font-mono">
                                                                        {typeof value === 'boolean' ? (value ? 'True' : 'False') : value}
                                                                    </span>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                    <div className="flex flex-col justify-between items-start gap-4">
                                                        <div className="w-full">
                                                            <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-2 font-semibold">Actions</h4>
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    handleRunBacktest(result);
                                                                }}
                                                                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 rounded-lg text-white font-medium transition-all shadow-lg shadow-blue-900/30 text-sm"
                                                            >
                                                                <Play className="w-4 h-4" />
                                                                Run Full Backtest
                                                            </button>
                                                        </div>
                                                    </div>
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                </>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
