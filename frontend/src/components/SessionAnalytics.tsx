import { useState, useMemo } from 'react';
import { ChevronDown, ChevronUp, ArrowDown, ArrowUp } from 'lucide-react';
import { type Trade } from '../api';

interface SessionAnalyticsProps {
    trades: Trade[];
    initialEquity?: number;
    multiMode?: boolean;
}

/* ── DST-aware "reference hour" ──────────────────────────────────
   All configured times in the app use "reference Brussels time", i.e.
   when Brussels – US/Eastern = 6 h.  During the ~3 weeks where the
   offset drops to 5 h (DST transition), wall-clock Brussels time is
   shifted by –1 h to stay in the reference frame.
   This ensures trades that happen at "the same market moment" always
   land in the same hourly bucket regardless of clock changes.
   ─────────────────────────────────────────────────────────────── */

const brusselsFmt = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Brussels',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
});

const etFmt = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'America/New_York',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
});

function parseHHMM(s: string): number {
    const [h, m] = s.split(':').map(Number);
    return h * 60 + m;
}

function getReferenceHour(entryTime: string): number {
    const date = new Date(entryTime);

    const bMinutes = parseHHMM(brusselsFmt.format(date));
    const etMinutes = parseHHMM(etFmt.format(date));

    let diff = bMinutes - etMinutes;
    if (diff < 0) diff += 24 * 60;
    const diffHours = Math.round(diff / 60);

    // diff=6 → standard (offset 0), diff=5 → DST shifted (offset +1)
    // When diff=5, Brussels wall clock is 1h early vs reference → add 1h to normalize
    const offset = diffHours === 6 ? 0 : 1;

    let refMinutes = bMinutes + offset * 60;
    if (refMinutes < 0) refMinutes += 24 * 60;
    if (refMinutes >= 24 * 60) refMinutes -= 24 * 60;

    return Math.floor(refMinutes / 60);
}

function formatHourSlot(hour: number): string {
    const h1 = hour.toString().padStart(2, '0');
    const h2 = ((hour + 1) % 24).toString().padStart(2, '0');
    return `${h1}:00 – ${h2}:00`;
}

/* Session reference hour ranges */
const SESSION_HOURS: Record<string, [number, number]> = {
    Asia: [0, 8],   // 00:00 – 08:59
    UK: [9, 15],    // 09:00 – 15:29
    US: [15, 22],   // 15:30 – end (we'll include 15 since some trades start at 15:30+)
};

interface HourBucket {
    hour: number;
    trades: Trade[];
    totalPnl: number;
    winCount: number;
}

interface SessionGroup {
    session: string;
    trades: Trade[];
    hours: HourBucket[];
    totalPnl: number;
    winRate: number;
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

function SideBadge({ side }: { side: string }) {
    const isLong = side === 'Long';
    return (
        <span className={`flex items-center gap-1 w-fit px-2 py-0.5 rounded text-[11px] font-bold border ${
            isLong ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'
        }`}>
            {isLong ? <ArrowUp className="w-2.5 h-2.5" /> : <ArrowDown className="w-2.5 h-2.5" />}
            {side}
        </span>
    );
}

const SESSION_STYLES: Record<string, { header: string; badge: string }> = {
    Asia: { header: 'from-yellow-600/20 to-transparent', badge: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' },
    UK: { header: 'from-blue-600/20 to-transparent', badge: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
    US: { header: 'from-purple-600/20 to-transparent', badge: 'bg-purple-500/10 text-purple-400 border-purple-500/20' },
};

export function SessionAnalytics({ trades, initialEquity = 50000, multiMode = false }: SessionAnalyticsProps) {
    const [expanded, setExpanded] = useState(true);
    const [expandedSessions, setExpandedSessions] = useState<Set<string>>(new Set());
    const [expandedHours, setExpandedHours] = useState<Set<string>>(new Set());

    const toggleSession = (session: string) => {
        setExpandedSessions(prev => {
            const next = new Set(prev);
            if (next.has(session)) next.delete(session);
            else next.add(session);
            return next;
        });
    };

    const toggleHour = (key: string) => {
        setExpandedHours(prev => {
            const next = new Set(prev);
            if (next.has(key)) next.delete(key);
            else next.add(key);
            return next;
        });
    };

    const sessionGroups: SessionGroup[] = useMemo(() => {
        const activeTrades = trades.filter(t => !t.excluded);

        return ['Asia', 'UK', 'US'].map(session => {
            const sessionTrades = activeTrades.filter(t => t.session === session);

            // Group by reference hour
            const hourMap = new Map<number, Trade[]>();
            sessionTrades.forEach(t => {
                const h = getReferenceHour(t.entry_execution_time || t.entry_time);
                if (!hourMap.has(h)) hourMap.set(h, []);
                hourMap.get(h)!.push(t);
            });

            // Sort hours
            const [start, end] = SESSION_HOURS[session];
            const hours: HourBucket[] = [];
            for (let h = start; h <= end; h++) {
                const hTrades = hourMap.get(h) || [];
                if (hTrades.length === 0) continue;
                hours.push({
                    hour: h,
                    trades: hTrades,
                    totalPnl: hTrades.reduce((sum, t) => sum + t.pnl, 0),
                    winCount: hTrades.filter(t => t.pnl > 0).length,
                });
            }

            // Also include any hours outside the expected range (edge cases)
            hourMap.forEach((hTrades, h) => {
                if (h < start || h > end) {
                    hours.push({
                        hour: h,
                        trades: hTrades,
                        totalPnl: hTrades.reduce((sum, t) => sum + t.pnl, 0),
                        winCount: hTrades.filter(t => t.pnl > 0).length,
                    });
                }
            });

            hours.sort((a, b) => a.hour - b.hour);

            const totalPnl = sessionTrades.reduce((sum, t) => sum + t.pnl, 0);
            const winRate = sessionTrades.length > 0
                ? (sessionTrades.filter(t => t.pnl > 0).length / sessionTrades.length) * 100
                : 0;

            return { session, trades: sessionTrades, hours, totalPnl, winRate };
        });
    }, [trades]);

    return (
        <div className="glass-panel rounded-xl overflow-hidden">
            <div className="p-5 border-b border-gray-700/50 bg-gray-800/30 flex items-center justify-between">
                <button
                    onClick={() => setExpanded(!expanded)}
                    className="flex items-center gap-2 text-gray-400 hover:text-gray-200 transition-colors"
                    aria-expanded={expanded}
                >
                    {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    <div>
                        <h3 className="text-sm uppercase tracking-wider font-semibold text-left">
                            Session Analytics — Hourly Breakdown
                        </h3>
                        <p className="text-[11px] text-gray-500 mt-1 text-left">
                            Trades grouped by reference Brussels hour (DST-adjusted). Useful for refining blackout windows.
                        </p>
                    </div>
                </button>
            </div>

            {expanded && <div className="divide-y divide-gray-700/30">
                {sessionGroups.map(group => {
                    const isExpanded = expandedSessions.has(group.session);
                    const styles = SESSION_STYLES[group.session];

                    return (
                        <div key={group.session}>
                            {/* Session header */}
                            <button
                                onClick={() => toggleSession(group.session)}
                                className={`w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors bg-gradient-to-r ${styles.header}`}
                            >
                                <div className="flex items-center gap-3">
                                    {isExpanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                                    <span className={`px-2.5 py-1 rounded-md text-xs font-bold border ${styles.badge}`}>
                                        {group.session}
                                    </span>
                                    <span className="text-gray-400 text-sm">
                                        {group.trades.length} trades
                                    </span>
                                    <span className="text-gray-500 text-xs">
                                        ({group.hours.length} active hours)
                                    </span>
                                </div>
                                <div className="flex items-center gap-4 text-sm font-mono">
                                    <span className="text-gray-500">
                                        WR {group.winRate.toFixed(0)}%
                                    </span>
                                    <span className={`font-bold ${group.totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                        {group.totalPnl >= 0 ? '+' : ''}{group.totalPnl.toFixed(2)}
                                    </span>
                                    <span className={`text-xs ${group.totalPnl >= 0 ? 'text-green-400/70' : 'text-red-400/70'}`}>
                                        ({((group.totalPnl / initialEquity) * 100).toFixed(2)}%)
                                    </span>
                                </div>
                            </button>

                            {/* Hour buckets */}
                            {isExpanded && (
                                <div className="bg-gray-950/30">
                                    {group.hours.length === 0 ? (
                                        <div className="p-6 text-center text-gray-500 text-sm">No trades in this session</div>
                                    ) : (
                                        group.hours.map(bucket => {
                                            const hourKey = `${group.session}-${bucket.hour}`;
                                            const isHourExpanded = expandedHours.has(hourKey);
                                            const winRate = bucket.trades.length > 0
                                                ? (bucket.winCount / bucket.trades.length) * 100
                                                : 0;

                                            return (
                                                <div key={hourKey} className="border-t border-gray-800/50">
                                                    {/* Hour header */}
                                                    <button
                                                        onClick={() => toggleHour(hourKey)}
                                                        className="w-full flex items-center justify-between px-6 py-3 hover:bg-white/3 transition-colors"
                                                    >
                                                        <div className="flex items-center gap-3">
                                                            {isHourExpanded
                                                                ? <ChevronUp className="w-3.5 h-3.5 text-gray-500" />
                                                                : <ChevronDown className="w-3.5 h-3.5 text-gray-500" />
                                                            }
                                                            <span className="text-gray-300 text-sm font-mono font-medium">
                                                                {formatHourSlot(bucket.hour)}
                                                            </span>
                                                            <span className="text-gray-500 text-xs">
                                                                {bucket.trades.length} trade{bucket.trades.length !== 1 ? 's' : ''}
                                                            </span>
                                                        </div>
                                                        <div className="flex items-center gap-4 text-xs font-mono">
                                                            <span className="text-gray-500">
                                                                WR {winRate.toFixed(0)}%
                                                            </span>
                                                            <span className={`font-bold ${bucket.totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                {bucket.totalPnl >= 0 ? '+' : ''}{bucket.totalPnl.toFixed(2)}
                                                            </span>
                                                            <span className={`${bucket.totalPnl >= 0 ? 'text-green-400/70' : 'text-red-400/70'}`}>
                                                                ({((bucket.totalPnl / initialEquity) * 100).toFixed(2)}%)
                                                            </span>
                                                        </div>
                                                    </button>

                                                    {/* Trades in this hour */}
                                                    {isHourExpanded && (
                                                        <div className="px-6 pb-3">
                                                            <table className="w-full text-left text-xs whitespace-nowrap">
                                                                <thead className="text-gray-500">
                                                                    <tr>
                                                                        <th className="py-1.5 px-2 font-medium">Entry</th>
                                                                        <th className="py-1.5 px-2 font-medium">Exit</th>
                                                                        <th className="py-1.5 px-2 font-medium">Side</th>
                                                                        {multiMode && <th className="py-1.5 px-2 font-medium">Source</th>}
                                                                        <th className="py-1.5 px-2 font-medium text-right">Entry Price</th>
                                                                        <th className="py-1.5 px-2 font-medium text-right">Exit Price</th>
                                                                        <th className="py-1.5 px-2 font-medium text-right">Size</th>
                                                                        <th className="py-1.5 px-2 font-medium">Status</th>
                                                                        <th className="py-1.5 px-2 font-medium text-right">Net PnL</th>
                                                                    </tr>
                                                                </thead>
                                                                <tbody className="divide-y divide-gray-800/50">
                                                                    {bucket.trades.map((t, i) => (
                                                                        <tr key={i} className="hover:bg-white/3 transition-colors">
                                                                            <td className="py-2 px-2 font-mono text-gray-300">
                                                                                {formatTimestamp(t.entry_execution_time || t.entry_time)}
                                                                            </td>
                                                                            <td className="py-2 px-2 font-mono text-gray-300">
                                                                                {formatTimestamp(t.exit_execution_time || t.exit_time)}
                                                                            </td>
                                                                            <td className="py-2 px-2">
                                                                                <SideBadge side={t.side} />
                                                                            </td>
                                                                            {multiMode && (
                                                                                <td className="py-2 px-2">
                                                                                    {t.source && (
                                                                                        <span className={`px-1.5 py-0.5 rounded text-xs font-bold border ${
                                                                                            t.source === '1'
                                                                                                ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                                                                                                : 'bg-violet-500/10 text-violet-400 border-violet-500/20'
                                                                                        }`}>#{t.source}</span>
                                                                                    )}
                                                                                </td>
                                                                            )}
                                                                            <td className="py-2 px-2 text-right font-mono text-gray-300">
                                                                                {t.entry_price.toFixed(2)}
                                                                            </td>
                                                                            <td className="py-2 px-2 text-right font-mono text-gray-300">
                                                                                {t.exit_price.toFixed(2)}
                                                                            </td>
                                                                            <td className="py-2 px-2 text-right font-mono text-gray-500">
                                                                                {t.size?.toFixed(0) || '1'}
                                                                            </td>
                                                                            <td className="py-2 px-2 text-gray-400">
                                                                                {t.status}
                                                                            </td>
                                                                            <td className={`py-2 px-2 text-right font-mono font-bold ${t.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                                {t.pnl >= 0 ? '+' : ''}{t.pnl.toFixed(2)}
                                                                            </td>
                                                                        </tr>
                                                                    ))}
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>}
        </div>
    );
}
