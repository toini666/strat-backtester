import { useState, useEffect } from 'react';
import { History, TrendingUp, Calendar, Clock, ChevronRight, Loader2, RefreshCw, RotateCcw } from 'lucide-react';
import { api, type OptimizationHistoryItem, type OptimizationRunDetail } from '../api';
import { ConfirmModal } from './ui/Modal';
import { useToast, ToastContainer } from './ui/Toast';

interface OptimizationHistoryProps {
    onLoadRun: (run: OptimizationRunDetail) => void;
    onReuseRun?: (run: OptimizationRunDetail) => void;
}

export function OptimizationHistory({ onLoadRun, onReuseRun }: OptimizationHistoryProps) {
    const [history, setHistory] = useState<OptimizationHistoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadingRunId, setLoadingRunId] = useState<string | null>(null);
    const [reuseRunId, setReuseRunId] = useState<string | null>(null);
    const [error, setError] = useState('');

    // UI State
    const [deleteId, setDeleteId] = useState<string | null>(null);
    const { toasts, addToast, removeToast } = useToast();

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

    const handleReuseRun = async (e: React.MouseEvent, runId: string) => {
        e.stopPropagation();
        if (!onReuseRun) return;

        setReuseRunId(runId);
        try {
            const run = await api.getOptimizationRun(runId);
            onReuseRun(run);
        } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            addToast("Failed to load run configuration: " + message, 'error');
        } finally {
            setReuseRunId(null);
        }
    };

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

    const handleDeleteClick = (e: React.MouseEvent, runId: string) => {
        e.stopPropagation();
        setDeleteId(runId);
    };

    const confirmDelete = async () => {
        if (!deleteId) return;

        try {
            await api.deleteOptimizationRun(deleteId);
            setHistory(prev => prev.filter(item => item.id !== deleteId));
            addToast("Optimization run deleted successfully", 'success');
        } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            addToast("Failed to delete run: " + message, 'error');
        } finally {
            setDeleteId(null);
        }
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
            <ConfirmModal
                isOpen={!!deleteId}
                onClose={() => setDeleteId(null)}
                onConfirm={confirmDelete}
                title="Delete Optimization Run"
                message="Are you sure you want to delete this optimization run? This action cannot be undone."
                confirmText="Delete"
                variant="danger"
            />

            <ToastContainer toasts={toasts} onDismiss={removeToast} />

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
                        <div
                            key={item.id}
                            onClick={() => handleLoadRun(item.id)}
                            className={`w-full p-4 rounded-lg bg-gray-800/50 hover:bg-gray-800 border border-gray-700/30 hover:border-gray-600 transition-all text-left group relative cursor-pointer ${loadingRunId === item.id ? 'opacity-70 pointer-events-none' : ''}`}
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-gray-200 font-medium">{item.strategy_name}</span>
                                        <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-400">
                                            {item.source}
                                        </span>
                                        <span className="text-xs text-gray-400 px-1">
                                            {item.source === 'Topstep' ? `#${item.contract_id}` : item.ticker}
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

                                    <div className="flex items-center gap-2">
                                        {onReuseRun && (
                                            <button
                                                onClick={(e) => handleReuseRun(e, item.id)}
                                                disabled={!!reuseRunId}
                                                className="p-1.5 rounded-md hover:bg-blue-900/30 text-gray-600 hover:text-blue-400 transition-colors z-10"
                                                title="Reuse Configuration"
                                            >
                                                {reuseRunId === item.id ? (
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                ) : (
                                                    <RotateCcw className="w-4 h-4" />
                                                )}
                                            </button>
                                        )}

                                        {loadingRunId === item.id ? (
                                            <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                                        ) : null}

                                        <button
                                            onClick={(e) => handleDeleteClick(e, item.id)}
                                            className="p-1.5 rounded-md hover:bg-red-900/30 text-gray-600 hover:text-red-400 transition-colors z-10"
                                            title="Delete run"
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                <path d="M3 6h18"></path>
                                                <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                                                <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
