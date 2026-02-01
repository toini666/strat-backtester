import { useState, useEffect, useMemo } from 'react';
import { History, Calendar, Clock, Loader2, RefreshCw, RotateCcw, Star, Trash2, CheckSquare, Square } from 'lucide-react';
import { api, type OptimizationHistoryItem, type OptimizationRunDetail } from '../api';
import { ConfirmModal } from './ui/Modal';
import { useToast, ToastContainer } from './ui/Toast';

interface OptimizationHistoryProps {
    onLoadRun: (run: OptimizationRunDetail) => void;
    onReuseRun?: (run: OptimizationRunDetail) => void;
}

type SortOption = 'date_desc' | 'date_asc' | 'return_desc' | 'return_asc' | 'strategy' | 'ticker';

export function OptimizationHistory({ onLoadRun, onReuseRun }: OptimizationHistoryProps) {
    const [history, setHistory] = useState<OptimizationHistoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadingRunId, setLoadingRunId] = useState<string | null>(null);
    const [reuseRunId, setReuseRunId] = useState<string | null>(null);
    const [error, setError] = useState('');

    // Filter & Sort State
    const [filterStrategy, setFilterStrategy] = useState<string>('all');
    const [filterTicker, setFilterTicker] = useState<string>('all');
    const [filterInterval, setFilterInterval] = useState<string>('all');
    const [sortOption, setSortOption] = useState<SortOption>('date_desc');
    const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);

    // Selection State
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

    // UI State
    const [deleteId, setDeleteId] = useState<string | null>(null); // For single delete
    const [isBulkDeleting, setIsBulkDeleting] = useState(false);
    const { toasts, addToast, removeToast } = useToast();

    const fetchHistory = async () => {
        setLoading(true);
        setError('');
        try {
            const data = await api.getOptimizationHistory();
            setHistory(data);
            // Clear selection on refresh
            setSelectedIds(new Set());
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

    // Derived Lists for Filters
    const uniqueStrategies = useMemo(() => {
        const strategies = new Set(history.map(h => h.strategy_name));
        return Array.from(strategies).sort();
    }, [history]);

    const uniqueTickers = useMemo(() => {
        const tickers = new Set(history.map(h => h.source === 'Topstep' ? (h.contract_id ? `#${h.contract_id}` : h.ticker) : h.ticker));
        return Array.from(tickers).sort();
    }, [history]);

    const uniqueIntervals = useMemo(() => {
        const intervals = new Set(history.map(h => h.interval));
        return Array.from(intervals).sort(); // Basic sort, ideally custom sort 1m, 5m, 1h...
    }, [history]);

    // Filter and Sort Logic
    const filteredAndSortedHistory = useMemo(() => {
        let result = [...history];

        // 1. Filter
        if (showFavoritesOnly) {
            result = result.filter(h => h.is_favorite);
        }

        if (filterStrategy !== 'all') {
            result = result.filter(h => h.strategy_name === filterStrategy);
        }

        if (filterTicker !== 'all') {
            result = result.filter(h => {
                const displayTicker = h.source === 'Topstep' ? (h.contract_id ? `#${h.contract_id}` : h.ticker) : h.ticker;
                return displayTicker === filterTicker;
            });
        }

        if (filterInterval !== 'all') {
            result = result.filter(h => h.interval === filterInterval);
        }

        // 2. Sort
        result.sort((a, b) => {
            switch (sortOption) {
                case 'date_desc':
                    return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
                case 'date_asc':
                    return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
                case 'return_desc':
                    return b.best_return - a.best_return;
                case 'return_asc':
                    return a.best_return - b.best_return;
                case 'strategy':
                    return a.strategy_name.localeCompare(b.strategy_name);
                case 'ticker':
                    const tickerA = a.source === 'Topstep' ? `#${a.contract_id}` : a.ticker;
                    const tickerB = b.source === 'Topstep' ? `#${b.contract_id}` : b.ticker;
                    return tickerA.localeCompare(tickerB);
                default:
                    return 0;
            }
        });

        return result;
    }, [history, filterStrategy, filterTicker, filterInterval, sortOption, showFavoritesOnly]);

    // Handlers
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
        if (selectedIds.size > 0) return; // Prevent loading when selecting

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

    const handleDeleteClick = (e: React.MouseEvent, runId: string) => {
        e.stopPropagation();
        setDeleteId(runId);
    };

    const confirmDelete = async () => {
        if (deleteId) {
            // Single Delete
            try {
                await api.deleteOptimizationRun(deleteId);
                setHistory(prev => prev.filter(item => item.id !== deleteId));
                setSelectedIds(prev => {
                    const next = new Set(prev);
                    next.delete(deleteId);
                    return next;
                });
                addToast("Optimization run deleted successfully", 'success');
            } catch (err) {
                const message = err instanceof Error ? err.message : String(err);
                addToast("Failed to delete run: " + message, 'error');
            } finally {
                setDeleteId(null);
            }
        } else if (isBulkDeleting) {
            // Bulk Delete
            try {
                const idsToDelete = Array.from(selectedIds);
                await api.bulkDeleteOptimizationRuns(idsToDelete);
                setHistory(prev => prev.filter(item => !selectedIds.has(item.id)));
                setSelectedIds(new Set());
                addToast(`Deleted ${idsToDelete.length} runs successfully`, 'success');
            } catch (err) {
                const message = err instanceof Error ? err.message : String(err);
                addToast("Failed to delete runs: " + message, 'error');
            } finally {
                setIsBulkDeleting(false);
            }
        }
    };

    const startBulkDelete = () => {
        if (selectedIds.size === 0) return;
        setIsBulkDeleting(true);
    };

    const toggleFavorite = async (e: React.MouseEvent, runId: string) => {
        e.stopPropagation();
        try {
            const newState = await api.toggleOptimizationFavorite(runId);
            setHistory(prev => prev.map(item =>
                item.id === runId ? { ...item, is_favorite: newState } : item
            ));
        } catch (err) {
            console.error("Failed to toggle favorite", err);
            addToast("Failed to update favorite status", 'error');
        }
    };

    const toggleSelection = (e: React.MouseEvent, runId: string) => {
        e.stopPropagation();
        setSelectedIds(prev => {
            const next = new Set(prev);
            if (next.has(runId)) {
                next.delete(runId);
            } else {
                next.add(runId);
            }
            return next;
        });
    };

    const toggleSelectAll = () => {
        if (selectedIds.size === filteredAndSortedHistory.length && filteredAndSortedHistory.length > 0) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(filteredAndSortedHistory.map(h => h.id)));
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
        <div className="glass-panel rounded-xl p-6 flex flex-col h-full max-h-[800px]">
            <ConfirmModal
                isOpen={!!deleteId || isBulkDeleting}
                onClose={() => { setDeleteId(null); setIsBulkDeleting(false); }}
                onConfirm={confirmDelete}
                title={isBulkDeleting ? "Delete Multiple Runs" : "Delete Optimization Run"}
                message={isBulkDeleting
                    ? `Are you sure you want to delete ${selectedIds.size} selected runs? This action cannot be undone.`
                    : "Are you sure you want to delete this optimization run? This action cannot be undone."
                }
                confirmText="Delete"
                variant="danger"
            />

            <ToastContainer toasts={toasts} onDismiss={removeToast} />

            {/* Header & Controls */}
            <div className="flex flex-col gap-4 mb-4 border-b border-gray-700/50 pb-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-amber-600/20 rounded-lg">
                            <History className="w-5 h-5 text-amber-400" />
                        </div>
                        <h2 className="text-lg font-semibold text-gray-200">Optimization History</h2>
                        <span className="bg-gray-800 text-gray-400 text-xs px-2 py-0.5 rounded-full">
                            {history.length}
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        {selectedIds.size > 0 && (
                            <button
                                onClick={startBulkDelete}
                                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-900/30 hover:bg-red-900/50 text-red-400 border border-red-800/30 transition-colors text-sm"
                            >
                                <Trash2 className="w-4 h-4" />
                                <span>Delete ({selectedIds.size})</span>
                            </button>
                        )}
                        <button
                            onClick={fetchHistory}
                            className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors"
                            title="Refresh history"
                        >
                            <RefreshCw className="w-4 h-4 text-gray-400" />
                        </button>
                    </div>
                </div>

                {/* Filters & Sort Bar */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                    {/* Strategy Filter */}
                    <select
                        value={filterStrategy}
                        onChange={(e) => setFilterStrategy(e.target.value)}
                        className="bg-gray-900/50 border border-gray-700 text-gray-300 text-xs rounded-lg p-2 focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none"
                    >
                        <option value="all">All Strategies</option>
                        {uniqueStrategies.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>

                    {/* Ticker Filter */}
                    <select
                        value={filterTicker}
                        onChange={(e) => setFilterTicker(e.target.value)}
                        className="bg-gray-900/50 border border-gray-700 text-gray-300 text-xs rounded-lg p-2 focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none"
                    >
                        <option value="all">All Tickers</option>
                        {uniqueTickers.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>

                    {/* Interval Filter */}
                    <select
                        value={filterInterval}
                        onChange={(e) => setFilterInterval(e.target.value)}
                        className="bg-gray-900/50 border border-gray-700 text-gray-300 text-xs rounded-lg p-2 focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none"
                    >
                        <option value="all">All Intervals</option>
                        {uniqueIntervals.map(i => <option key={i} value={i}>{i}</option>)}
                    </select>

                    {/* Favorites Toggle */}
                    <button
                        onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
                        className={`flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg border transition-colors text-xs ${showFavoritesOnly
                            ? 'bg-yellow-900/30 border-yellow-700/50 text-yellow-500'
                            : 'bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700'
                            }`}
                        title="Show favorites only"
                    >
                        <Star className={`w-3.5 h-3.5 ${showFavoritesOnly ? 'fill-yellow-500' : ''}`} />
                        <span>Favorites</span>
                    </button>

                    {/* Sort Toggle */}
                    <select
                        value={sortOption}
                        onChange={(e) => setSortOption(e.target.value as SortOption)}
                        className="bg-gray-900/50 border border-gray-700 text-gray-300 text-xs rounded-lg p-2 focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none"
                    >
                        <option value="date_desc">Newest First</option>
                        <option value="date_asc">Oldest First</option>
                        <option value="return_desc">Best Return</option>
                        <option value="return_asc">Worst Return</option>
                        <option value="strategy">Strategy Name</option>
                        <option value="ticker">Ticker</option>
                    </select>
                </div>
            </div>

            {error && (
                <div className="mb-4 p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-red-400 text-sm">
                    {error}
                </div>
            )}

            {/* Content List */}
            {filteredAndSortedHistory.length === 0 ? (
                <div className="text-center py-12 flex-1 flex flex-col justify-center">
                    <History className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                    <p className="text-gray-500">No matching runs found</p>
                    {history.length > 0 && (
                        <button
                            onClick={() => {
                                setFilterStrategy('all');
                                setFilterTicker('all');
                                setFilterInterval('all');
                                setShowFavoritesOnly(false);
                            }}
                            className="text-amber-500 text-xs mt-2 hover:underline"
                        >
                            Clear filters
                        </button>
                    )}
                </div>
            ) : (
                <div className="flex-1 overflow-visible min-h-0 flex flex-col">
                    {/* List Header with Select All */}
                    <div className="flex items-center px-4 py-2 border-b border-gray-700/30 text-xs font-semibold text-gray-500 uppercase tracking-wider bg-gray-900/20 rounded-t-lg">
                        <div className="flex items-center gap-3 w-8">
                            <button onClick={toggleSelectAll} className="p-0.5 rounded hover:bg-gray-700/50 text-gray-400">
                                {selectedIds.size > 0 && selectedIds.size === filteredAndSortedHistory.length ? (
                                    <CheckSquare className="w-4 h-4 text-amber-500" />
                                ) : (
                                    <Square className="w-4 h-4" />
                                )}
                            </button>
                        </div>
                        <div className="flex-1">Description</div>
                        <div className="text-right w-24">Return</div>
                        <div className="w-24 text-right">Actions</div>
                    </div>

                    <div className="overflow-y-auto pr-2 space-y-1 mt-2 flex-1 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
                        {filteredAndSortedHistory.map((item) => (
                            <div
                                key={item.id}
                                onClick={() => handleLoadRun(item.id)}
                                className={`w-full p-3 rounded-lg flex items-center gap-3 transition-all text-left group relative cursor-pointer border
                                    ${selectedIds.has(item.id)
                                        ? 'bg-amber-900/10 border-amber-500/30'
                                        : 'bg-gray-800/40 hover:bg-gray-800 border-gray-700/30 hover:border-gray-600'}
                                    ${loadingRunId === item.id ? 'opacity-70 pointer-events-none' : ''}
                                `}
                            >
                                {/* Checkbox & Favorite */}
                                <div className="flex flex-col gap-2 items-center justify-center w-8 shrink-0" onClick={(e) => e.stopPropagation()}>
                                    <button
                                        onClick={(e) => toggleSelection(e, item.id)}
                                        className="text-gray-500 hover:text-gray-300"
                                    >
                                        {selectedIds.has(item.id) ? (
                                            <CheckSquare className="w-4 h-4 text-amber-500" />
                                        ) : (
                                            <Square className="w-4 h-4" />
                                        )}
                                    </button>
                                    <button
                                        onClick={(e) => toggleFavorite(e, item.id)}
                                        className={`transition-colors ${item.is_favorite ? 'text-yellow-500' : 'text-gray-600 hover:text-yellow-500/50'}`}
                                    >
                                        <Star className={`w-4 h-4 ${item.is_favorite ? 'fill-yellow-500' : ''}`} />
                                    </button>
                                </div>

                                {/* Main Content */}
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                                        <span className="text-gray-200 font-medium truncate">{item.strategy_name}</span>
                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-700 text-gray-400 shrink-0">
                                            {item.source}
                                        </span>
                                        <span className="text-[10px] text-gray-400 px-1 border border-gray-700 rounded shrink-0">
                                            {item.source === 'Topstep' ? `#${item.contract_id}` : item.ticker}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-4 text-xs text-gray-500 flex-wrap">
                                        <span className="flex items-center gap-1 shrink-0">
                                            <Calendar className="w-3 h-3" />
                                            {formatDate(item.timestamp)}
                                        </span>
                                        <span className="flex items-center gap-1 shrink-0">
                                            <Clock className="w-3 h-3" />
                                            {item.interval}
                                            <span className="text-gray-600 px-1">|</span>
                                            {item.start_date && item.end_date
                                                ? (
                                                    <span title={`${item.start_date} - ${item.end_date}`}>
                                                        {Math.max(0, Math.ceil((new Date(item.end_date).getTime() - new Date(item.start_date).getTime()) / (1000 * 60 * 60 * 24))) + 1}d
                                                    </span>
                                                )
                                                : `${item.days}d`
                                            }
                                        </span>
                                        <span className="text-gray-600 shrink-0">
                                            {item.total_combinations.toLocaleString()} combos
                                        </span>
                                    </div>
                                </div>

                                {/* Return & Actions */}
                                <div className="flex items-center gap-4 shrink-0">
                                    <div className="text-right w-20">
                                        <div className={`text-sm font-bold font-mono ${item.best_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                            {item.best_return >= 0 ? '+' : ''}{item.best_return.toFixed(2)}%
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                                        {onReuseRun && (
                                            <button
                                                onClick={(e) => handleReuseRun(e, item.id)}
                                                disabled={!!reuseRunId}
                                                className="p-1.5 rounded-md hover:bg-blue-900/30 text-gray-600 hover:text-blue-400 transition-colors"
                                                title="Reuse Configuration"
                                            >
                                                {reuseRunId === item.id ? (
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                ) : (
                                                    <RotateCcw className="w-4 h-4" />
                                                )}
                                            </button>
                                        )}

                                        <button
                                            onClick={(e) => handleDeleteClick(e, item.id)}
                                            className="p-1.5 rounded-md hover:bg-red-900/30 text-gray-600 hover:text-red-400 transition-colors"
                                            title="Delete run"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
