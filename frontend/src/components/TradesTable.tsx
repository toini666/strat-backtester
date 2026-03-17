import { Fragment, useState, useMemo } from 'react';
import { ArrowDown, ArrowUp, ChevronDown, ChevronUp, Filter } from 'lucide-react';
import { type Trade, type TradeLeg } from '../api';

type PnlFilter = 'all' | 'positive' | 'negative';
type SideFilter = 'all' | 'long' | 'short';

interface TradesTableProps {
    trades: Trade[];
    selectedSessions: string[];
    onSessionsChange: (sessions: string[]) => void;
}

const timeFormatter = new Intl.DateTimeFormat('fr-BE', {
    timeZone: 'Europe/Brussels',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
});

function formatTimestamp(value?: string | null): string {
    if (!value) return 'n/a';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return timeFormatter.format(date).replace(',', '');
}

function TimeCell({
    barTime,
    execTime,
    label,
}: {
    barTime?: string | null;
    execTime?: string | null;
    label?: string;
}) {
    return (
        <div className="space-y-1">
            <div className="text-gray-200 font-mono text-xs">{formatTimestamp(barTime)}</div>
            <div className="text-[11px] text-gray-500 font-mono">
                {label || 'exec'}: {formatTimestamp(execTime || barTime)}
            </div>
        </div>
    );
}

function SideBadge({ side }: { side: string }) {
    const isLong = side === 'Long';
    return (
        <span className={`flex items-center gap-1 w-fit px-2 py-1 rounded-md text-xs font-bold border ${
            isLong ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'
        }`}>
            {isLong ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
            {side}
        </span>
    );
}

function SessionBadge({ session }: { session: string }) {
    return (
        <span className={`px-2 py-1 rounded-md text-xs font-bold border ${
            session === 'Asia' ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                : session === 'UK' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                    : session === 'US' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20'
                        : 'bg-gray-600/10 text-gray-400 border-gray-600/20'
        }`}>
            {session}
        </span>
    );
}

const SESSION_COLORS: Record<string, { bg: string; text: string; border: string; checked: string }> = {
    Asia: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', border: 'border-yellow-500/30', checked: 'bg-yellow-500/25' },
    UK: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30', checked: 'bg-blue-500/25' },
    US: { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/30', checked: 'bg-purple-500/25' },
};

function SessionMultiSelect({
    selected,
    onChange,
}: {
    selected: string[];
    onChange: (sessions: string[]) => void;
}) {
    const sessions = ['Asia', 'UK', 'US'];

    const toggle = (sess: string) => {
        if (selected.includes(sess)) {
            onChange(selected.filter(s => s !== sess));
        } else {
            onChange([...selected, sess]);
        }
    };

    return (
        <div className="flex items-center gap-1.5">
            {sessions.map(sess => {
                const colors = SESSION_COLORS[sess];
                const isActive = selected.includes(sess);
                return (
                    <button
                        key={sess}
                        onClick={() => toggle(sess)}
                        className={`px-2.5 py-1 rounded-md text-xs font-bold border transition-all ${
                            isActive
                                ? `${colors.checked} ${colors.text} ${colors.border}`
                                : 'bg-gray-800/50 text-gray-500 border-gray-700/50 hover:text-gray-400'
                        }`}
                    >
                        {sess}
                    </button>
                );
            })}
        </div>
    );
}

function LegRow({ leg, excluded }: { leg: TradeLeg; excluded?: boolean }) {
    return (
        <tr className={`bg-gray-950/40 ${excluded ? 'opacity-35' : ''}`}>
            <td className="p-4 pl-10">
                <TimeCell barTime={leg.entry_time} execTime={leg.entry_execution_time} label="entry" />
            </td>
            <td className="p-4">
                <TimeCell barTime={leg.exit_time} execTime={leg.exit_execution_time} />
            </td>
            <td className="p-4 text-gray-500 text-xs">leg</td>
            <td className="p-4">
                <SideBadge side={leg.side} />
            </td>
            <td className="p-4 text-right font-mono text-gray-300">{leg.entry_price.toFixed(2)}</td>
            <td className="p-4 text-right font-mono text-gray-300">{leg.exit_price.toFixed(2)}</td>
            <td className="p-4 text-right font-mono text-gray-500">{leg.size.toFixed(0)}</td>
            <td className="p-4 text-xs text-gray-400">{leg.status}</td>
            <td className={`p-4 text-right font-mono font-bold ${leg.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {leg.pnl >= 0 ? '+' : ''}{leg.pnl.toFixed(2)}
            </td>
        </tr>
    );
}

export function TradesTable({ trades, selectedSessions, onSessionsChange }: TradesTableProps) {
    const [expanded, setExpanded] = useState(false);
    const [pnlFilter, setPnlFilter] = useState<PnlFilter>('all');
    const [sideFilter, setSideFilter] = useState<SideFilter>('all');

    const filteredTrades = useMemo(() => {
        return trades.filter(t => {
            if (pnlFilter === 'positive' && t.pnl <= 0) return false;
            if (pnlFilter === 'negative' && t.pnl >= 0) return false;
            if (sideFilter === 'long' && t.side !== 'Long') return false;
            if (sideFilter === 'short' && t.side !== 'Short') return false;
            return true;
        });
    }, [trades, pnlFilter, sideFilter]);

    const filterCounts = useMemo(() => ({
        all: trades.length,
        positive: trades.filter(t => t.pnl > 0).length,
        negative: trades.filter(t => t.pnl < 0).length,
    }), [trades]);

    const sideCounts = useMemo(() => ({
        all: trades.length,
        long: trades.filter(t => t.side === 'Long').length,
        short: trades.filter(t => t.side === 'Short').length,
    }), [trades]);

    return (
        <div className="glass-panel rounded-xl overflow-hidden">
            {/* Header */}
            <div className="p-5 border-b border-gray-700/50 bg-gray-800/30 flex items-center justify-between gap-4 flex-wrap">
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setExpanded(!expanded)}
                        className="flex items-center gap-2 text-gray-400 hover:text-gray-200 transition-colors"
                        aria-expanded={expanded}
                        aria-controls="trade-history-body"
                    >
                        {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        <h3 className="text-sm uppercase tracking-wider font-semibold">Trade History</h3>
                    </button>
                    <span className="text-gray-500 text-xs font-mono">
                        {filteredTrades.length} / {trades.length} trades
                        {trades.some(t => t.excluded) && (
                            <span className="text-yellow-500 ml-1">
                                ({trades.filter(t => t.excluded).length} excluded)
                            </span>
                        )}
                    </span>
                </div>

                <div className="flex items-center gap-4">
                    {/* PnL Filter */}
                    <div className="flex items-center gap-1.5">
                        <Filter className="w-3.5 h-3.5 text-gray-500" />
                        {(['all', 'positive', 'negative'] as PnlFilter[]).map(f => (
                            <button
                                key={f}
                                onClick={() => setPnlFilter(f)}
                                className={`px-2.5 py-1 rounded-md text-xs font-medium border transition-all ${
                                    pnlFilter === f
                                        ? f === 'positive'
                                            ? 'bg-green-500/15 text-green-400 border-green-500/30'
                                            : f === 'negative'
                                                ? 'bg-red-500/15 text-red-400 border-red-500/30'
                                                : 'bg-gray-700/50 text-gray-300 border-gray-600/50'
                                        : 'bg-gray-800/50 text-gray-500 border-gray-700/50 hover:text-gray-400'
                                }`}
                            >
                                {f === 'all' ? `All (${filterCounts.all})`
                                    : f === 'positive' ? `Win (${filterCounts.positive})`
                                        : `Loss (${filterCounts.negative})`}
                            </button>
                        ))}
                    </div>

                    {/* Side Filter */}
                    <div className="flex items-center gap-1.5">
                        {(['all', 'long', 'short'] as SideFilter[]).map(f => (
                            <button
                                key={f}
                                onClick={() => setSideFilter(f)}
                                className={`px-2.5 py-1 rounded-md text-xs font-medium border transition-all ${
                                    sideFilter === f
                                        ? f === 'long'
                                            ? 'bg-green-500/15 text-green-400 border-green-500/30'
                                            : f === 'short'
                                                ? 'bg-red-500/15 text-red-400 border-red-500/30'
                                                : 'bg-gray-700/50 text-gray-300 border-gray-600/50'
                                        : 'bg-gray-800/50 text-gray-500 border-gray-700/50 hover:text-gray-400'
                                }`}
                            >
                                {f === 'all' ? `All (${sideCounts.all})`
                                    : f === 'long' ? `Long (${sideCounts.long})`
                                        : `Short (${sideCounts.short})`}
                            </button>
                        ))}
                    </div>

                    {/* Session Multi-Select */}
                    <SessionMultiSelect selected={selectedSessions} onChange={onSessionsChange} />
                </div>
            </div>

            {/* Body */}
            {expanded && (
                <div id="trade-history-body">
                    <table className="w-full text-left text-sm whitespace-nowrap">
                        <thead className="bg-gray-900/80 backdrop-blur text-gray-400">
                            <tr>
                                <th className="p-4 font-medium">Entry Bar</th>
                                <th className="p-4 font-medium">Exit Bar</th>
                                <th className="p-4 font-medium">Session</th>
                                <th className="p-4 font-medium">Side</th>
                                <th className="p-4 font-medium text-right">Entry</th>
                                <th className="p-4 font-medium text-right">Exit</th>
                                <th className="p-4 font-medium text-right">Size</th>
                                <th className="p-4 font-medium">Status</th>
                                <th className="p-4 font-medium text-right">Net PnL</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700/30">
                            {filteredTrades.map((trade, index) => {
                                const legs = trade.legs || [];
                                const showLegs = legs.length > 1;
                                const isExcluded = trade.excluded === true;
                                return (
                                    <Fragment key={`trade-${index}`}>
                                        <tr className={`transition-colors ${isExcluded ? 'opacity-35' : 'hover:bg-white/5'}`}
                                            title={isExcluded ? 'Excluded — daily limit reached' : undefined}
                                        >
                                            <td className="p-4">
                                                <TimeCell barTime={trade.entry_time} execTime={trade.entry_execution_time} label="entry" />
                                            </td>
                                            <td className="p-4">
                                                <TimeCell barTime={trade.exit_time} execTime={trade.exit_execution_time} />
                                            </td>
                                            <td className="p-4">
                                                <SessionBadge session={trade.session} />
                                            </td>
                                            <td className="p-4">
                                                <SideBadge side={trade.side} />
                                            </td>
                                            <td className="p-4 text-right font-mono text-gray-300">{trade.entry_price.toFixed(2)}</td>
                                            <td className="p-4 text-right font-mono text-gray-300">{trade.exit_price.toFixed(2)}</td>
                                            <td className="p-4 text-right font-mono text-gray-500">{trade.size?.toFixed(0) || '1'}</td>
                                            <td className="p-4 text-xs text-gray-300">
                                                <div>{trade.status}</div>
                                                {showLegs && (
                                                    <div className="text-[11px] text-gray-500 mt-1">{legs.length} legs</div>
                                                )}
                                            </td>
                                            <td className={`p-4 text-right font-mono font-bold ${trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                                            </td>
                                        </tr>
                                        {showLegs && legs.map((leg, legIndex) => (
                                            <LegRow key={`trade-${index}-leg-${legIndex}`} leg={leg} excluded={isExcluded} />
                                        ))}
                                    </Fragment>
                                );
                            })}
                        </tbody>
                    </table>
                    {filteredTrades.length === 0 && (
                        <div className="p-12 text-center text-gray-500 flex flex-col items-center justify-center">
                            <p>{trades.length === 0 ? 'No trades recorded' : 'No trades match the current filters'}</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
