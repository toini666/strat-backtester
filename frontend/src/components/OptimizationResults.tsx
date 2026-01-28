import { useState } from 'react';
import { Trophy, TrendingUp, Activity, Hash, TrendingDown, ArrowLeft, Play } from 'lucide-react';
import { type OptimizationResultItem } from '../api';

interface OptimizationResultsProps {
    results: OptimizationResultItem[];
    strategyName: string;
    totalCombinations: number;
    completed: number;
    errors: number;
    onSelectResult: (result: OptimizationResultItem) => void;
    onBack: () => void;
}

export function OptimizationResults({
    results,
    strategyName,
    totalCombinations,
    completed,
    errors,
    onSelectResult,
    onBack
}: OptimizationResultsProps) {
    const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

    const handleRowClick = (result: OptimizationResultItem, index: number) => {
        setSelectedIndex(index);
    };

    const handleRunBacktest = () => {
        if (selectedIndex !== null && results[selectedIndex]) {
            onSelectResult(results[selectedIndex]);
        }
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
                            {strategyName} • {completed.toLocaleString()} combinations tested
                            {errors > 0 && <span className="text-red-400"> • {errors} errors</span>}
                        </p>
                    </div>
                </div>

                {selectedIndex !== null && (
                    <button
                        onClick={handleRunBacktest}
                        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 rounded-lg text-white font-medium transition-all shadow-lg shadow-blue-900/30"
                    >
                        <Play className="w-4 h-4" />
                        View Full Backtest
                    </button>
                )}
            </div>

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
                                <th className="px-4 py-3 text-left font-medium">Parameters</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700/30">
                            {results.map((result, index) => (
                                <tr
                                    key={index}
                                    onClick={() => handleRowClick(result, index)}
                                    className={`cursor-pointer transition-colors ${
                                        selectedIndex === index
                                            ? 'bg-blue-900/30 border-l-2 border-l-blue-500'
                                            : 'hover:bg-white/5'
                                    }`}
                                >
                                    <td className="px-4 py-3">
                                        <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                                            result.rank === 1 ? 'bg-yellow-500/20 text-yellow-400' :
                                            result.rank === 2 ? 'bg-gray-400/20 text-gray-300' :
                                            result.rank === 3 ? 'bg-orange-500/20 text-orange-400' :
                                            'bg-gray-800 text-gray-500'
                                        }`}>
                                            {result.rank}
                                        </span>
                                    </td>
                                    <td className={`px-4 py-3 text-right font-mono font-bold ${
                                        result.total_return >= 0 ? 'text-green-400' : 'text-red-400'
                                    }`}>
                                        {result.total_return >= 0 ? '+' : ''}{result.total_return.toFixed(2)}%
                                    </td>
                                    <td className="px-4 py-3 text-right font-mono text-blue-400">
                                        {result.win_rate.toFixed(1)}%
                                    </td>
                                    <td className="px-4 py-3 text-right font-mono text-orange-400">
                                        {result.trade_count}
                                    </td>
                                    <td className={`px-4 py-3 text-right font-mono ${
                                        result.max_drawdown > -5 ? 'text-green-400' :
                                        result.max_drawdown > -15 ? 'text-yellow-400' : 'text-red-400'
                                    }`}>
                                        {result.max_drawdown.toFixed(2)}%
                                    </td>
                                    <td className="px-4 py-3">
                                        <div className="flex gap-1 flex-wrap">
                                            {result.sessions.map(sess => (
                                                <span
                                                    key={sess}
                                                    className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                                                        sess === 'Asia' ? 'bg-pink-500/20 text-pink-400' :
                                                        sess === 'UK' ? 'bg-blue-500/20 text-blue-400' :
                                                        'bg-green-500/20 text-green-400'
                                                    }`}
                                                >
                                                    {sess}
                                                </span>
                                            ))}
                                        </div>
                                    </td>
                                    <td className="px-4 py-3">
                                        <div className="flex gap-1 flex-wrap max-w-[300px]">
                                            {Object.entries(result.parameters).slice(0, 4).map(([key, value]) => (
                                                <span
                                                    key={key}
                                                    className="px-2 py-0.5 text-xs bg-gray-800 rounded text-gray-400 font-mono"
                                                    title={`${key}: ${value}`}
                                                >
                                                    {key.split('_').map(w => w[0]).join('')}={String(value).slice(0, 6)}
                                                </span>
                                            ))}
                                            {Object.keys(result.parameters).length > 4 && (
                                                <span className="px-2 py-0.5 text-xs bg-gray-800 rounded text-gray-500">
                                                    +{Object.keys(result.parameters).length - 4}
                                                </span>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Selected Result Details */}
            {selectedIndex !== null && results[selectedIndex] && (
                <div className="glass-panel rounded-xl p-6 border-2 border-blue-600/50 bg-blue-900/10">
                    <h3 className="text-lg font-semibold text-gray-200 mb-4">
                        Selected Configuration (Rank #{results[selectedIndex].rank})
                    </h3>
                    <div className="grid grid-cols-2 gap-6">
                        <div>
                            <h4 className="text-sm text-gray-400 uppercase tracking-wider mb-3">Parameters</h4>
                            <div className="space-y-2">
                                {Object.entries(results[selectedIndex].parameters).map(([key, value]) => (
                                    <div key={key} className="flex justify-between items-center">
                                        <span className="text-gray-400 font-mono text-sm">{key}</span>
                                        <span className="text-gray-200 font-mono font-medium bg-gray-800 px-2 py-0.5 rounded">
                                            {typeof value === 'boolean' ? (value ? 'True' : 'False') : value}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div>
                            <h4 className="text-sm text-gray-400 uppercase tracking-wider mb-3">Sessions</h4>
                            <div className="flex gap-2">
                                {results[selectedIndex].sessions.map(sess => (
                                    <span
                                        key={sess}
                                        className={`px-3 py-1.5 rounded-lg font-medium ${
                                            sess === 'Asia' ? 'bg-pink-500/20 text-pink-400' :
                                            sess === 'UK' ? 'bg-blue-500/20 text-blue-400' :
                                            'bg-green-500/20 text-green-400'
                                        }`}
                                    >
                                        {sess}
                                    </span>
                                ))}
                            </div>

                            <h4 className="text-sm text-gray-400 uppercase tracking-wider mt-6 mb-3">Performance</h4>
                            <div className="grid grid-cols-2 gap-3">
                                <div className="bg-gray-800/50 rounded-lg p-3">
                                    <div className="text-xs text-gray-500">Return</div>
                                    <div className={`text-lg font-bold font-mono ${
                                        results[selectedIndex].total_return >= 0 ? 'text-green-400' : 'text-red-400'
                                    }`}>
                                        {results[selectedIndex].total_return >= 0 ? '+' : ''}
                                        {results[selectedIndex].total_return.toFixed(2)}%
                                    </div>
                                </div>
                                <div className="bg-gray-800/50 rounded-lg p-3">
                                    <div className="text-xs text-gray-500">Win Rate</div>
                                    <div className="text-lg font-bold font-mono text-blue-400">
                                        {results[selectedIndex].win_rate.toFixed(1)}%
                                    </div>
                                </div>
                                <div className="bg-gray-800/50 rounded-lg p-3">
                                    <div className="text-xs text-gray-500">Trades</div>
                                    <div className="text-lg font-bold font-mono text-orange-400">
                                        {results[selectedIndex].trade_count}
                                    </div>
                                </div>
                                <div className="bg-gray-800/50 rounded-lg p-3">
                                    <div className="text-xs text-gray-500">Max DD</div>
                                    <div className="text-lg font-bold font-mono text-purple-400">
                                        {results[selectedIndex].max_drawdown.toFixed(2)}%
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <p className="text-sm text-gray-500 mt-4">
                        Click "View Full Backtest" to run a detailed simulation with these parameters.
                    </p>
                </div>
            )}
        </div>
    );
}
