import { useState, useEffect, useCallback, useMemo, Fragment } from 'react';
import { AlertTriangle, CalendarClock, ChevronDown, ChevronRight, ShieldAlert } from 'lucide-react';
import { api, type MarketDataset } from '../api';

const dateTimeFormatter = new Intl.DateTimeFormat('fr-BE', {
    timeZone: 'Europe/Brussels',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
});

function formatDateTime(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return dateTimeFormatter.format(date).replace(',', '');
}

function freshnessLabel(dataset: MarketDataset): { label: string; classes: string } {
    if (dataset.retention_exceeded) {
        return {
            label: 'Retention exceeded',
            classes: 'bg-red-500/10 text-red-300 border-red-500/20',
        };
    }
    if (dataset.retention_warning) {
        return {
            label: 'Retention soon',
            classes: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
        };
    }
    return {
        label: 'Healthy',
        classes: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20',
    };
}

export function MarketDataPanel() {
    const [datasets, setDatasets] = useState<MarketDataset[]>([]);
    const [error, setError] = useState('');
    const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

    const toggleExpand = (id: string) => {
        setExpandedRows((prev) => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    };

    const fetchDatasets = useCallback(async () => {
        try {
            const data = await api.getMarketData();
            setDatasets(data);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : String(err);
            setError(message);
        }
    }, []);

    useEffect(() => {
        fetchDatasets();
    }, [fetchDatasets]);

    const summary = useMemo(() => {
        const warningCount = datasets.filter((dataset) => dataset.retention_warning || dataset.retention_exceeded).length;
        const maxMissingDays = datasets.reduce((max, dataset) => Math.max(max, dataset.missing_days), 0);
        const freshest = datasets.reduce<MarketDataset | null>((best, dataset) => {
            if (!best || dataset.missing_hours < best.missing_hours) {
                return dataset;
            }
            return best;
        }, null);
        return {
            warningCount,
            maxMissingDays,
            freshest,
        };
    }, [datasets]);

    const handleDelete = async (datasetId: string) => {
        if (!confirm('Delete this dataset?')) return;
        try {
            await api.deleteMarketData(datasetId);
            fetchDatasets();
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : String(err);
            setError(message);
        }
    };

    const COL_COUNT = 10;

    return (
        <div className="space-y-6">

            {summary.warningCount > 0 && (
                <div className="glass-panel rounded-xl p-4 border border-amber-700/40 bg-amber-900/10 text-amber-200 flex gap-3">
                    <AlertTriangle className="w-5 h-5 shrink-0 text-amber-400" />
                    <div>
                        <div className="font-semibold">Retention warning</div>
                        <div className="text-sm text-amber-100/80">
                            {summary.warningCount} dataset(s) are close to or beyond the 60-day retention window. Refresh them soon to avoid losing historical coverage.
                        </div>
                    </div>
                </div>
            )}

            {error && (
                <div className="p-4 bg-red-900/30 border border-red-700/50 rounded-lg text-red-400 text-sm">
                    {error}
                    <button onClick={() => setError('')} className="ml-4 text-red-300 hover:text-red-200">Dismiss</button>
                </div>
            )}

            <div className="glass-panel rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4 text-cyan-400 font-semibold">
                    <CalendarClock className="w-5 h-5" />
                    <h2>Available Datasets</h2>
                </div>

                {datasets.length === 0 ? (
                    <p className="text-gray-500 text-sm text-center py-8">
                        No datasets available.
                    </p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-gray-400 border-b border-gray-800">
                                    <th className="text-left py-2 px-3 font-medium w-6"></th>
                                    <th className="text-left py-2 px-3 font-medium">Symbol</th>
                                    <th className="text-left py-2 px-3 font-medium">Contract</th>
                                    <th className="text-left py-2 px-3 font-medium">Coverage Start</th>
                                    <th className="text-left py-2 px-3 font-medium">Coverage End</th>
                                    <th className="text-left py-2 px-3 font-medium">Timeframes</th>
                                    <th className="text-right py-2 px-3 font-medium">Bars 1m</th>
                                    <th className="text-right py-2 px-3 font-medium">Missing</th>
                                    <th className="text-left py-2 px-3 font-medium">Status</th>
                                    <th className="text-left py-2 px-3 font-medium">Updated</th>
                                    <th className="text-center py-2 px-3 font-medium">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {datasets.map((dataset) => {
                                    const freshness = freshnessLabel(dataset);
                                    const segments = dataset.contract_segments || [];
                                    const hasMultipleContracts = segments.length > 1;
                                    const isExpanded = expandedRows.has(dataset.id);
                                    const lastSegment = segments.length > 0 ? segments[segments.length - 1] : null;
                                    return (
                                        <Fragment key={dataset.id}>
                                            <tr className="border-b border-gray-800/50 hover:bg-gray-800/30 align-top">
                                                <td className="py-3 px-3">
                                                    {hasMultipleContracts ? (
                                                        <button
                                                            onClick={() => toggleExpand(dataset.id)}
                                                            className="text-gray-500 hover:text-gray-300 transition-colors"
                                                        >
                                                            {isExpanded
                                                                ? <ChevronDown className="w-4 h-4" />
                                                                : <ChevronRight className="w-4 h-4" />}
                                                        </button>
                                                    ) : null}
                                                </td>
                                                <td className="py-3 px-3 text-gray-100 font-semibold">{dataset.symbol}</td>
                                                <td className="py-3 px-3">
                                                    <div className="text-gray-300 font-mono text-xs">
                                                        {lastSegment ? lastSegment.label : dataset.contract_id}
                                                    </div>
                                                    {hasMultipleContracts && (
                                                        <div className="text-[11px] text-gray-500 mt-0.5">
                                                            {segments.length} contracts
                                                        </div>
                                                    )}
                                                </td>
                                                <td className="py-3 px-3 text-gray-300 font-mono text-xs">{formatDateTime(dataset.start_date)}</td>
                                                <td className="py-3 px-3 text-gray-300 font-mono text-xs">{formatDateTime(dataset.end_date)}</td>
                                                <td className="py-3 px-3 text-gray-400 text-xs">{dataset.timeframes.join(', ')}</td>
                                                <td className="py-3 px-3 text-gray-300 text-right">{dataset.bar_count_1m.toLocaleString()}</td>
                                                <td className="py-3 px-3 text-right">
                                                    <div className="text-gray-100 font-semibold">{dataset.missing_days.toFixed(1)}d</div>
                                                    <div className="text-xs text-gray-500">{dataset.missing_hours.toFixed(1)}h</div>
                                                </td>
                                                <td className="py-3 px-3">
                                                    <span className={`inline-flex px-2 py-1 rounded-md text-xs font-bold border ${freshness.classes}`}>
                                                        {freshness.label}
                                                    </span>
                                                    <div className="text-xs text-gray-500 mt-1">
                                                        {dataset.retention_exceeded
                                                            ? `${Math.abs(dataset.days_until_retention_limit).toFixed(1)}d past limit`
                                                            : `${dataset.days_until_retention_limit.toFixed(1)}d before limit`}
                                                    </div>
                                                </td>
                                                <td className="py-3 px-3 text-gray-400 text-xs font-mono">{formatDateTime(dataset.updated_at)}</td>
                                                <td className="py-3 px-3 text-center">
                                                    <button
                                                        onClick={() => handleDelete(dataset.id)}
                                                        className="text-red-400 hover:text-red-300 text-xs px-2 py-1 rounded hover:bg-red-900/30 transition-colors inline-flex items-center gap-1"
                                                    >
                                                        <ShieldAlert className="w-3 h-3" />
                                                        Delete
                                                    </button>
                                                </td>
                                            </tr>
                                            {isExpanded && segments.map((seg, i) => (
                                                <tr key={`${dataset.id}-seg-${i}`} className="bg-gray-900/40 border-b border-gray-800/30">
                                                    <td className="py-2 px-3"></td>
                                                    <td className="py-2 px-3"></td>
                                                    <td className="py-2 px-3">
                                                        <span className="text-cyan-400 font-mono text-xs font-semibold">{seg.label}</span>
                                                    </td>
                                                    <td className="py-2 px-3 text-gray-400 font-mono text-xs">{seg.from}</td>
                                                    <td className="py-2 px-3 text-gray-400 font-mono text-xs">{seg.to}</td>
                                                    <td colSpan={COL_COUNT - 5} className="py-2 px-3 text-gray-500 font-mono text-xs">{seg.contract}</td>
                                                </tr>
                                            ))}
                                        </Fragment>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
