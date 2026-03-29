import { useState, useEffect, useRef } from 'react';
import {
    AlertCircle,
    ArrowUpDown,
    Check,
    ChevronDown,
    ChevronUp,
    ClipboardCopy,
    Pencil,
    RotateCcw,
    Search,
    Star,
    Trash2,
    Upload,
} from 'lucide-react';
import { ConfirmModal } from './ui/Modal';
import {
    type BacktestMode,
    type BacktestPreset,
    type SingleBacktestPreset,
    type MultiBacktestPreset,
    type PresetMetrics,
    loadPresets,
    loadPresetsLocal,
    savePreset,
    deletePreset as deletePresetFromStorage,
    renamePreset,
} from '../api';

interface MultiContext {
    backtestMode: BacktestMode;
    activeSlot: 0 | 1;
    slotLabel: string;          // "Asset 1", "Strategy 2", etc.
    lockedSymbol?: string;      // multi_strat: both slots must use this ticker
    otherSlotSymbol?: string;   // multi_asset: the other slot's current ticker
}

interface FavoritesPageProps {
    onLoadPreset: (preset: BacktestPreset) => void;
    multiContext?: MultiContext;
}

type SortKey = 'name' | 'strategyName' | 'symbol' | 'interval' | 'createdAt';
type SortDir = 'asc' | 'desc';

/** Module-level cache — survives navigation but NOT page reload */
const _filterCache: {
    filterMode: '' | 'single' | 'multi_asset' | 'multi_strat';
    filterStrategy: string;
    filterTicker: string;
    filterTimeframe: string;
    sortKey: SortKey;
    sortDir: SortDir;
} = {
    filterMode: '',
    filterStrategy: '',
    filterTicker: '',
    filterTimeframe: '',
    sortKey: 'createdAt',
    sortDir: 'desc',
};

/** Unified display fields for both single and multi presets */
function getPresetInfo(preset: BacktestPreset) {
    if (preset.mode === 'multi_asset' || preset.mode === 'multi_strat') {
        const mp = preset as MultiBacktestPreset;
        const [c1, c2] = mp.configs;
        return {
            strategyName: `${c1.strategyName} / ${c2.strategyName}`,
            symbol: `${c1.symbol} / ${c2.symbol}`,
            interval: `${c1.interval} / ${c2.interval}`,
            startDatetime: mp.startDatetime,
            endDatetime: mp.endDatetime,
            isMulti: true,
            modeLabel: preset.mode === 'multi_asset' ? 'Multi-Asset' : 'Multi-Strat',
            modeColor: preset.mode === 'multi_asset'
                ? 'text-violet-400 bg-violet-500/10 border-violet-500/20'
                : 'text-fuchsia-400 bg-fuchsia-500/10 border-fuchsia-500/20',
        };
    }
    const sp = preset as SingleBacktestPreset;
    return {
        strategyName: sp.strategyName,
        symbol: sp.symbol,
        interval: sp.interval,
        startDatetime: sp.startDatetime,
        endDatetime: sp.endDatetime,
        isMulti: false,
        modeLabel: 'Single',
        modeColor: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
    };
}

function fmt$(amount: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
}

function MetricsBadges({ metrics, initialEquity }: { metrics: PresetMetrics; initialEquity: number }) {
    const retColor = metrics.total_return >= 0 ? 'text-green-400' : 'text-red-400';
    const retUsd = metrics.total_return / 100 * initialEquity;
    const ddUsd = metrics.max_drawdown / 100 * initialEquity;
    return (
        <div className="flex flex-wrap gap-1 min-w-[200px]">
            <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-gray-700/60 ${retColor}`}>
                {metrics.total_return >= 0 ? '+' : ''}{metrics.total_return.toFixed(1)}% <span className="font-normal opacity-70">({metrics.total_return >= 0 ? '+' : ''}{fmt$(retUsd)})</span>
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-gray-700/60 text-gray-300">
                {metrics.total_trades} trades
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-gray-700/60 text-red-400">
                DD {metrics.max_drawdown.toFixed(1)}% <span className="font-normal opacity-70">({fmt$(ddUsd)})</span>
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-gray-700/60 text-blue-300">
                WR {metrics.win_rate.toFixed(0)}%
            </span>
        </div>
    );
}

export function FavoritesPage({ onLoadPreset, multiContext }: FavoritesPageProps) {
    const [presets, setPresets] = useState<BacktestPreset[]>(() => loadPresetsLocal());
    const [filterMode, _setFilterMode] = useState<'' | 'single' | 'multi_asset' | 'multi_strat'>(_filterCache.filterMode);
    const [filterStrategy, _setFilterStrategy] = useState(_filterCache.filterStrategy);
    const [filterTicker, _setFilterTicker] = useState(_filterCache.filterTicker);
    const [filterTimeframe, _setFilterTimeframe] = useState(_filterCache.filterTimeframe);
    const [sortKey, _setSortKey] = useState<SortKey>(_filterCache.sortKey);
    const [sortDir, _setSortDir] = useState<SortDir>(_filterCache.sortDir);

    const setFilterMode = (v: '' | 'single' | 'multi_asset' | 'multi_strat') => { _filterCache.filterMode = v; _setFilterMode(v); };
    const setFilterStrategy = (v: string) => { _filterCache.filterStrategy = v; _setFilterStrategy(v); };
    const setFilterTicker = (v: string) => { _filterCache.filterTicker = v; _setFilterTicker(v); };
    const setFilterTimeframe = (v: string) => { _filterCache.filterTimeframe = v; _setFilterTimeframe(v); };
    const setSortKey = (v: SortKey) => { _filterCache.sortKey = v; _setSortKey(v); };
    const setSortDir = (fn: SortDir | ((prev: SortDir) => SortDir)) => {
        const next = typeof fn === 'function' ? fn(_filterCache.sortDir) : fn;
        _filterCache.sortDir = next;
        _setSortDir(next);
    };
    const [renamingId, setRenamingId] = useState<string | null>(null);
    const [renameValue, setRenameValue] = useState('');
    const renameInputRef = useRef<HTMLInputElement>(null);
    const [copiedId, setCopiedId] = useState<string | null>(null);
    const [deleteConfirmPreset, setDeleteConfirmPreset] = useState<BacktestPreset | null>(null);
    const [loadError, setLoadError] = useState<{ presetId: string; message: string } | null>(null);
    const loadErrorTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
    const [importOpen, setImportOpen] = useState(false);
    const [importText, setImportText] = useState('');
    const [importError, setImportError] = useState('');

    useEffect(() => {
        loadPresets().then(setPresets);
    }, []);

    // Derive unique filter options from existing presets
    const uniqueStrategies = [...new Set(presets.map(p => getPresetInfo(p).strategyName))].sort();
    const uniqueTickers = [...new Set(presets.map(p => getPresetInfo(p).symbol))].sort();
    const uniqueTimeframes = [...new Set(presets.map(p => getPresetInfo(p).interval))].sort();

    const filtered = presets
        .filter(p => !filterMode || (filterMode === 'single' ? (!p.mode || p.mode === 'single') : p.mode === filterMode))
        .filter(p => !filterStrategy || getPresetInfo(p).strategyName === filterStrategy)
        .filter(p => !filterTicker || getPresetInfo(p).symbol === filterTicker)
        .filter(p => !filterTimeframe || getPresetInfo(p).interval === filterTimeframe)
        .sort((a, b) => {
            const infoA = getPresetInfo(a);
            const infoB = getPresetInfo(b);
            let valA: string | number = sortKey === 'createdAt' ? a.createdAt : (sortKey === 'name' ? a.name : (infoA as Record<string, string>)[sortKey] ?? '');
            let valB: string | number = sortKey === 'createdAt' ? b.createdAt : (sortKey === 'name' ? b.name : (infoB as Record<string, string>)[sortKey] ?? '');
            if (typeof valA === 'string') valA = valA.toLowerCase();
            if (typeof valB === 'string') valB = valB.toLowerCase();
            if (valA < valB) return sortDir === 'asc' ? -1 : 1;
            if (valA > valB) return sortDir === 'asc' ? 1 : -1;
            return 0;
        });

    const handleSort = (key: SortKey) => {
        if (sortKey === key) {
            setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        } else {
            setSortKey(key);
            setSortDir('asc');
        }
    };

    const startRenaming = (preset: BacktestPreset) => {
        setRenamingId(preset.id);
        setRenameValue(preset.name);
        setTimeout(() => renameInputRef.current?.select(), 0);
    };

    const commitRename = async (id: string) => {
        const trimmed = renameValue.trim();
        if (trimmed) {
            const updated = await renamePreset(id, trimmed);
            setPresets(updated);
        }
        setRenamingId(null);
    };

    const handleCopy = (preset: BacktestPreset) => {
        navigator.clipboard.writeText(JSON.stringify(preset, null, 2));
        setCopiedId(preset.id);
        setTimeout(() => setCopiedId(null), 2000);
    };

    const handleDelete = async (id: string) => {
        const updated = await deletePresetFromStorage(id);
        setPresets(updated);
        setDeleteConfirmPreset(null);
    };

    const handleImport = async () => {
        setImportError('');
        let parsed: BacktestPreset;
        try {
            parsed = JSON.parse(importText);
        } catch {
            setImportError('JSON invalide');
            return;
        }
        // Accept both single and multi presets
        const isMulti = parsed.mode === 'multi_asset' || parsed.mode === 'multi_strat';
        const isSingle = !isMulti && (parsed as SingleBacktestPreset).strategyName;
        if (!isMulti && !isSingle) {
            setImportError('Preset incomplet (strategyName ou configs manquant)');
            return;
        }
        const fresh: BacktestPreset = {
            ...parsed,
            id: crypto.randomUUID(),
            createdAt: new Date().toISOString(),
        };
        const updated = await savePreset(fresh);
        setPresets(updated);
        setImportText('');
        setImportOpen(false);
    };

    const showLoadError = (presetId: string, message: string) => {
        if (loadErrorTimer.current) clearTimeout(loadErrorTimer.current);
        setLoadError({ presetId, message });
        loadErrorTimer.current = setTimeout(() => setLoadError(null), 4000);
    };

    /** Validate and trigger preset load, with conflict checks in multi mode */
    const handleReuse = (preset: BacktestPreset) => {
        const isSingle = !preset.mode || preset.mode === 'single';
        if (multiContext && isSingle) {
            const sp = preset as SingleBacktestPreset;
            if (multiContext.backtestMode === 'multi_strat' && multiContext.lockedSymbol && sp.symbol !== multiContext.lockedSymbol) {
                showLoadError(preset.id,
                    `Ce preset utilise ${sp.symbol} mais les deux strats sont sur ${multiContext.lockedSymbol} — impossible à charger.`
                );
                return;
            }
            if (multiContext.backtestMode === 'multi_asset' && multiContext.otherSlotSymbol && sp.symbol === multiContext.otherSlotSymbol) {
                showLoadError(preset.id,
                    `Ce preset utilise ${sp.symbol} qui est déjà sélectionné dans l'autre asset — chaque asset doit avoir un ticker différent.`
                );
                return;
            }
        }
        setLoadError(null);
        onLoadPreset(preset);
    };

    const SortIcon = ({ col }: { col: SortKey }) => {
        if (sortKey !== col) return <ArrowUpDown className="w-3.5 h-3.5 text-gray-600" />;
        return sortDir === 'asc'
            ? <ChevronUp className="w-3.5 h-3.5 text-amber-400" />
            : <ChevronDown className="w-3.5 h-3.5 text-amber-400" />;
    };

    const ColHeader = ({ col, label }: { col: SortKey; label: string }) => (
        <th
            onClick={() => handleSort(col)}
            className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider cursor-pointer select-none hover:text-gray-200 transition-colors whitespace-nowrap"
        >
            <span className="flex items-center gap-1.5">
                {label}
                <SortIcon col={col} />
            </span>
        </th>
    );

    return (
        <>
        <div className="space-y-5">
            {/* Multi-mode context banner */}
            {multiContext && (
                <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-lg bg-violet-500/10 border border-violet-500/25 text-xs text-violet-300">
                    <RotateCcw className="w-3.5 h-3.5 shrink-0" />
                    <span>
                        Mode <span className="font-semibold">{multiContext.backtestMode === 'multi_asset' ? 'Multi-Asset' : 'Multi-Strat'}</span> actif —
                        les presets single seront chargés dans <span className="font-semibold">{multiContext.slotLabel}</span> sans changer l'autre slot ni les dates.
                    </span>
                </div>
            )}
            {/* Page header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-amber-500/20 rounded-lg border border-amber-500/30">
                        <Star className="w-5 h-5 text-amber-400 fill-amber-400" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-gray-100">Favorites</h2>
                        <p className="text-xs text-gray-500">
                            {filtered.length} preset{filtered.length !== 1 ? 's' : ''}
                            {presets.length !== filtered.length ? ` / ${presets.length} total` : ''}
                        </p>
                    </div>
                </div>
                <button
                    onClick={() => { setImportOpen(!importOpen); setImportError(''); setImportText(''); }}
                    className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors py-2 px-3 rounded-lg hover:bg-gray-700/40 border border-gray-700/50"
                >
                    <Upload className="w-4 h-4" />
                    Import JSON
                </button>
            </div>

            {/* Import panel */}
            {importOpen && (
                <div className="glass-panel rounded-xl p-4 space-y-3 border border-amber-500/20">
                    <h3 className="text-sm font-medium text-amber-400">Importer un preset</h3>
                    <textarea
                        value={importText}
                        onChange={(e) => { setImportText(e.target.value); setImportError(''); }}
                        placeholder="Colle le JSON du preset ici..."
                        className="w-full h-28 text-xs text-gray-200 bg-gray-800/60 border border-gray-600 rounded-lg px-3 py-2 outline-none focus:border-amber-400/60 resize-none font-mono"
                    />
                    {importError && <p className="text-xs text-red-400">{importError}</p>}
                    <div className="flex gap-2 justify-end">
                        <button
                            onClick={() => setImportOpen(false)}
                            className="text-sm px-4 py-2 rounded-lg text-gray-400 hover:bg-gray-700/40 transition-colors"
                        >
                            Annuler
                        </button>
                        <button
                            onClick={handleImport}
                            disabled={!importText.trim()}
                            className="text-sm px-4 py-2 rounded-lg bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                            Ajouter
                        </button>
                    </div>
                </div>
            )}

            {/* Filters */}
            <div className="glass-panel rounded-xl p-4">
                <div className="flex items-center gap-4 flex-wrap">
                    <div className="flex items-center gap-2 text-xs text-gray-500 shrink-0">
                        <Search className="w-3.5 h-3.5" />
                        <span className="uppercase tracking-wider font-medium">Filtres</span>
                    </div>
                    {/* Mode filter */}
                    <div className="flex items-center gap-1.5">
                        {([
                            { value: '', label: 'Tous' },
                            { value: 'single', label: 'Single' },
                            { value: 'multi_asset', label: 'Multi-Asset' },
                            { value: 'multi_strat', label: 'Multi-Strat' },
                        ] as const).map(opt => (
                            <button
                                key={opt.value}
                                onClick={() => setFilterMode(opt.value)}
                                className={`px-2.5 py-1 rounded-md text-xs font-medium border transition-all ${
                                    filterMode === opt.value
                                        ? opt.value === 'multi_asset'
                                            ? 'bg-violet-500/15 text-violet-400 border-violet-500/30'
                                            : opt.value === 'multi_strat'
                                                ? 'bg-fuchsia-500/15 text-fuchsia-400 border-fuchsia-500/30'
                                                : opt.value === 'single'
                                                    ? 'bg-blue-500/15 text-blue-400 border-blue-500/30'
                                                    : 'bg-gray-700/50 text-gray-300 border-gray-600/50'
                                        : 'bg-gray-800/50 text-gray-500 border-gray-700/50 hover:text-gray-400'
                                }`}
                            >
                                {opt.label}
                            </button>
                        ))}
                    </div>

                    <div className="flex items-center gap-2">
                        <label className="text-xs text-gray-500 shrink-0">Strategy</label>
                        <select
                            className="input-base text-sm py-1.5 min-w-[140px]"
                            value={filterStrategy}
                            onChange={e => setFilterStrategy(e.target.value)}
                        >
                            <option value="">Toutes</option>
                            {uniqueStrategies.map(s => (
                                <option key={s} value={s}>{s}</option>
                            ))}
                        </select>
                    </div>
                    <div className="flex items-center gap-2">
                        <label className="text-xs text-gray-500 shrink-0">Ticker</label>
                        <select
                            className="input-base text-sm py-1.5 min-w-[100px]"
                            value={filterTicker}
                            onChange={e => setFilterTicker(e.target.value)}
                        >
                            <option value="">Tous</option>
                            {uniqueTickers.map(t => (
                                <option key={t} value={t}>{t}</option>
                            ))}
                        </select>
                    </div>
                    <div className="flex items-center gap-2">
                        <label className="text-xs text-gray-500 shrink-0">Timeframe</label>
                        <select
                            className="input-base text-sm py-1.5 min-w-[90px]"
                            value={filterTimeframe}
                            onChange={e => setFilterTimeframe(e.target.value)}
                        >
                            <option value="">Tous</option>
                            {uniqueTimeframes.map(tf => (
                                <option key={tf} value={tf}>{tf}</option>
                            ))}
                        </select>
                    </div>
                    {(filterMode || filterStrategy || filterTicker || filterTimeframe) && (
                        <button
                            onClick={() => { setFilterMode(''); setFilterStrategy(''); setFilterTicker(''); setFilterTimeframe(''); }}
                            className="text-xs text-gray-500 hover:text-gray-300 transition-colors px-2.5 py-1.5 rounded-lg hover:bg-gray-700/40 border border-gray-700/50"
                        >
                            Effacer les filtres
                        </button>
                    )}
                </div>
            </div>

            {/* Table */}
            <div className="glass-panel rounded-xl overflow-hidden">
                {filtered.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-20 text-center">
                        <div className="w-16 h-16 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mb-5">
                            <Star className="w-8 h-8 text-amber-400/40" />
                        </div>
                        <p className="text-gray-300 font-medium mb-2">
                            {presets.length === 0 ? 'Aucun preset sauvegardé' : 'Aucun résultat'}
                        </p>
                        <p className="text-xs text-gray-600 max-w-sm">
                            {presets.length === 0
                                ? "Utilisez le bouton \"Save\" dans l'onglet Backtest pour sauvegarder une configuration."
                                : 'Modifiez ou effacez les filtres pour voir plus de presets.'}
                        </p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="border-b border-gray-700/50 bg-gray-800/30">
                                <tr>
                                    <ColHeader col="name" label="Nom" />
                                    <ColHeader col="strategyName" label="Strategy" />
                                    <ColHeader col="symbol" label="Ticker" />
                                    <ColHeader col="interval" label="TF" />
                                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider whitespace-nowrap">Période</th>
                                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider whitespace-nowrap">Métriques</th>
                                    <ColHeader col="createdAt" label="Créé le" />
                                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-800/40">
                                {filtered.map(preset => {
                                    const info = getPresetInfo(preset);
                                    return (
                                    <tr key={preset.id} className="hover:bg-gray-800/20 transition-colors group">
                                        {/* Name + mode badge */}
                                        <td className="px-4 py-3 max-w-[220px]">
                                            {renamingId === preset.id ? (
                                                <input
                                                    ref={renameInputRef}
                                                    value={renameValue}
                                                    onChange={e => setRenameValue(e.target.value)}
                                                    onBlur={() => commitRename(preset.id)}
                                                    onKeyDown={e => {
                                                        if (e.key === 'Enter') commitRename(preset.id);
                                                        if (e.key === 'Escape') setRenamingId(null);
                                                    }}
                                                    className="w-full text-sm text-gray-100 bg-gray-700/60 border border-amber-400/50 rounded px-2 py-0.5 outline-none focus:border-amber-400"
                                                    autoFocus
                                                />
                                            ) : (
                                                <div className="flex flex-col gap-1">
                                                    <span className="text-sm text-gray-200 font-medium truncate">{preset.name}</span>
                                                    <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border w-fit ${info.modeColor}`}>
                                                        {info.modeLabel}
                                                    </span>
                                                </div>
                                            )}
                                        </td>
                                        {/* Strategy */}
                                        <td className="px-4 py-3">
                                            <span className="text-xs px-2 py-1 rounded-md bg-purple-500/15 text-purple-300 font-medium whitespace-nowrap">
                                                {info.strategyName}
                                            </span>
                                        </td>
                                        {/* Ticker */}
                                        <td className="px-4 py-3">
                                            <span className="text-xs px-2 py-1 rounded-md bg-blue-500/15 text-blue-300 font-medium font-mono">
                                                {info.symbol}
                                            </span>
                                        </td>
                                        {/* Timeframe */}
                                        <td className="px-4 py-3">
                                            <span className="text-xs px-2 py-1 rounded-md bg-cyan-500/15 text-cyan-300 font-medium font-mono">
                                                {info.interval}
                                            </span>
                                        </td>
                                        {/* Date range */}
                                        <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                                            <div>{info.startDatetime.replace('T', ' ')}</div>
                                            <div>{info.endDatetime.replace('T', ' ')}</div>
                                        </td>
                                        {/* Metrics */}
                                        <td className="px-4 py-3">
                                            {preset.metrics
                                                ? <MetricsBadges metrics={preset.metrics} initialEquity={preset.initialEquity} />
                                                : <span className="text-[10px] text-gray-600 italic">—</span>
                                            }
                                        </td>
                                        {/* Created */}
                                        <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                                            {new Date(preset.createdAt).toLocaleDateString('fr-FR')}
                                        </td>
                                        {/* Actions */}
                                        <td className="px-4 py-3">
                                            {loadError?.presetId === preset.id && (
                                                <div className="flex items-center gap-1.5 mb-1.5 text-[10px] text-red-400 bg-red-500/10 border border-red-500/20 rounded px-2 py-1">
                                                    <AlertCircle className="w-3 h-3 shrink-0" />
                                                    <span>{loadError.message}</span>
                                                </div>
                                            )}
                                            <div className="flex items-center gap-1 justify-end opacity-40 group-hover:opacity-100 transition-opacity">
                                                {(() => {
                                                    const isSingle = !preset.mode || preset.mode === 'single';
                                                    const isSlotLoad = multiContext && isSingle;
                                                    return (
                                                        <button
                                                            onClick={() => handleReuse(preset)}
                                                            className={`flex items-center gap-1 p-1.5 rounded-md transition-colors ${
                                                                isSlotLoad
                                                                    ? 'text-violet-400 hover:bg-violet-500/10'
                                                                    : 'text-blue-400 hover:bg-blue-500/10'
                                                            }`}
                                                            title={isSlotLoad
                                                                ? `Charger dans ${multiContext.slotLabel}`
                                                                : 'Charger ce preset'
                                                            }
                                                        >
                                                            <RotateCcw className="w-3.5 h-3.5" />
                                                            {isSlotLoad && (
                                                                <span className="text-[10px] font-medium leading-none">
                                                                    → {multiContext.slotLabel}
                                                                </span>
                                                            )}
                                                        </button>
                                                    );
                                                })()}
                                                <button
                                                    onClick={() => startRenaming(preset)}
                                                    className="p-1.5 rounded-md text-amber-400 hover:bg-amber-500/10 transition-colors"
                                                    title="Renommer"
                                                >
                                                    <Pencil className="w-3.5 h-3.5" />
                                                </button>
                                                <button
                                                    onClick={() => handleCopy(preset)}
                                                    className="p-1.5 rounded-md text-emerald-400 hover:bg-emerald-500/10 transition-colors"
                                                    title="Copier JSON"
                                                >
                                                    {copiedId === preset.id
                                                        ? <Check className="w-3.5 h-3.5" />
                                                        : <ClipboardCopy className="w-3.5 h-3.5" />}
                                                </button>
                                                <button
                                                    onClick={() => setDeleteConfirmPreset(preset)}
                                                    className="p-1.5 rounded-md text-red-400 hover:bg-red-500/10 transition-colors"
                                                    title="Supprimer"
                                                >
                                                    <Trash2 className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>

        <ConfirmModal
            isOpen={deleteConfirmPreset !== null}
            onClose={() => setDeleteConfirmPreset(null)}
            onConfirm={() => deleteConfirmPreset && handleDelete(deleteConfirmPreset.id)}
            title="Supprimer le preset"
            message={`Supprimer "${deleteConfirmPreset?.name}" ? Cette action est irréversible.`}
            confirmText="Supprimer"
            cancelText="Annuler"
            variant="danger"
        />
        </>
    );
}
