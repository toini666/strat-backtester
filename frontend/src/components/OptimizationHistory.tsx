import { useState, useEffect } from 'react';
import { History, TrendingUp, Calendar, Clock, ChevronRight, Loader2, RefreshCw } from 'lucide-react';
import { api, type OptimizationHistoryItem, type OptimizationRunDetail } from '../api';

interface OptimizationHistoryProps {
    onLoadRun: (run: OptimizationRunDetail) => void;
}

export function OptimizationHistory({ onLoadRun }: OptimizationHistoryProps) {
    const [history, setHistory] = useState<OptimizationHistoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadingRunId, setLoadingRunId] = useState<string | null>(null);
    const [error, setError] = useState('');

    const fetchHistory = async () => {
        setLoading(true);
        setError('');
        try {
            const data = await api.getOptimizationHistory();
            // Sort by timestamp descending (most recent first)
            data.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
            setHistory(data);
        } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchHistory();
    }, []);

    const handleLoadRun = async (runId: string) => {
        setLoadingRunId(runId);
        try {
            const run = await api.getOptimizationRun(runId);
            onLoadRun(run);
        } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            setError(message);
        } finally {
            setLoadingRunId(null);
        }
    };

    const formatDate = (timestamp: string) => {
        const date = new Date(timestamp);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    if (loading) {
        return (
            <div className="glass-panel rounded-xl p-6">
                <div className="flex items-center justify-center py-12 text-gray-500">
                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
                    Loading history...
                </div>
            </div>
        );
    }

    return (
        <div className="glass-panel rounded-xl p-6">
            <div className="flex items-center justify-between mb-4 border-b border-gray-700/50 pb-4">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-amber-600/20 rounded-lg">
                        <History className="w-5 h-5 text-amber-400" />
                    </div>
                    <h2 className="text-lg font-semibold text-gray-200">Optimization History</h2>
                </div>
                <button
                    onClick={fetchHistory}
                    className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors"
                    title="Refresh history"
                >
                    <RefreshCw className="w-4 h-4 text-gray-400" />
                </button>
            </div>

            {error && (
                <div className="mb-4 p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-red-400 text-sm">
                    {error}
                </div>
            )}

            {history.length === 0 ? (
                <div className="text-center py-12">
                    <History className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                    <p className="text-gray-500">No optimization runs yet</p>
                    <p className="text-gray-600 text-sm mt-1">Run an optimization to see history here</p>
                </div>
            ) : (
                <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2">
                    {history.map((item) => (
                        <button
                            key={item.id}
                            onClick={() => handleLoadRun(item.id)}
                            disabled={loadingRunId === item.id}
                            className="w-full p-4 rounded-lg bg-gray-800/50 hover:bg-gray-800 border border-gray-700/30 hover:border-gray-600 transition-all text-left group"
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-gray-200 font-medium">{item.strategy_name}</span>
                                        <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-400">
                                            {item.source}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-4 text-xs text-gray-500">
                                        <span className="flex items-center gap-1">
                                            <Calendar className="w-3 h-3" />
                                            {formatDate(item.timestamp)}
                                        </span>
                                        <span className="flex items-center gap-1">
                                            <Clock className="w-3 h-3" />
                                            {item.interval} / {item.days}d
                                        </span>
                                        <span className="text-gray-600">
                                            {item.total_combinations.toLocaleString()} combos
                                        </span>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="text-right">
                                        <div className={`text-sm font-bold font-mono ${item.best_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                            {item.best_return >= 0 ? '+' : ''}{item.best_return.toFixed(2)}%
                                        </div>
                                        <div className="text-xs text-gray-500">best return</div>
                                    </div>
                                    {loadingRunId === item.id ? (
                                        <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                                    ) : (
                                        <ChevronRight className="w-5 h-5 text-gray-600 group-hover:text-gray-400 transition-colors" />
                                    )}
                                </div>
                            </div>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
