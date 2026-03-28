import { useState, useMemo } from 'react';
import { ChevronDown, ChevronUp, ArrowUp, ArrowDown } from 'lucide-react';
import { type Trade } from '../api';

interface TradeAnalyticsProps {
    trades: Trade[];
    initialEquity?: number;
}

const brusselsDateFmt = new Intl.DateTimeFormat('fr-BE', {
    timeZone: 'Europe/Brussels',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
});

const brusselsDayFmt = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Europe/Brussels',
    weekday: 'long',
});

function getBrusselsDateKey(ts: string): string {
    return brusselsDateFmt.format(new Date(ts));
}

function getBrusselsDayOfWeek(ts: string): string {
    return brusselsDayFmt.format(new Date(ts));
}

function formatDuration(minutes: number): string {
    if (minutes < 60) return `${Math.round(minutes)}m`;
    const h = Math.floor(minutes / 60);
    const m = Math.round(minutes % 60);
    return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function MetricRow({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div className="flex items-center justify-between py-3 border-b border-gray-800/50 last:border-b-0">
            <span className="text-gray-400 text-sm">{label}</span>
            <div className="text-sm font-mono text-right">{children}</div>
        </div>
    );
}

function PnlValue({ value, prefix }: { value: number; prefix?: string }) {
    return (
        <span className={`font-bold ${value >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {prefix}{value >= 0 ? '+' : ''}{value.toFixed(2)}
        </span>
    );
}

export function TradeAnalytics({ trades }: TradeAnalyticsProps) {
    const [expanded, setExpanded] = useState(false);

    const analytics = useMemo(() => {
        const active = trades.filter(t => !t.excluded);
        if (active.length === 0) return null;

        const wins = active.filter(t => t.pnl > 0);
        const losses = active.filter(t => t.pnl < 0);

        // Avg win / avg loss
        const avgWin = wins.length > 0 ? wins.reduce((s, t) => s + t.pnl, 0) / wins.length : 0;
        const avgLoss = losses.length > 0 ? losses.reduce((s, t) => s + t.pnl, 0) / losses.length : 0;

        // Avg PnL per trading day
        const dayMap = new Map<string, number>();
        active.forEach(t => {
            const key = getBrusselsDateKey(t.entry_execution_time || t.entry_time);
            dayMap.set(key, (dayMap.get(key) || 0) + t.pnl);
        });
        const tradingDays = dayMap.size;
        const totalPnl = active.reduce((s, t) => s + t.pnl, 0);
        const avgPerDay = tradingDays > 0 ? totalPnl / tradingDays : 0;

        // Profit factor
        const totalGains = wins.reduce((s, t) => s + t.pnl, 0);
        const totalLosses = Math.abs(losses.reduce((s, t) => s + t.pnl, 0));
        const profitFactor = totalLosses > 0 ? totalGains / totalLosses : totalGains > 0 ? Infinity : 0;

        // Best/worst day of week (Mon-Fri aggregate)
        const dowMap = new Map<string, number>();
        active.forEach(t => {
            const dow = getBrusselsDayOfWeek(t.entry_execution_time || t.entry_time);
            dowMap.set(dow, (dowMap.get(dow) || 0) + t.pnl);
        });
        let bestDow = { day: '-', pnl: -Infinity };
        let worstDow = { day: '-', pnl: Infinity };
        dowMap.forEach((pnl, day) => {
            if (pnl > bestDow.pnl) bestDow = { day, pnl };
            if (pnl < worstDow.pnl) worstDow = { day, pnl };
        });

        // Best/worst actual date
        let bestDate = { date: '-', pnl: -Infinity };
        let worstDate = { date: '-', pnl: Infinity };
        dayMap.forEach((pnl, date) => {
            if (pnl > bestDate.pnl) bestDate = { date, pnl };
            if (pnl < worstDate.pnl) worstDate = { date, pnl };
        });

        // Direction stats
        const longs = active.filter(t => t.side === 'Long');
        const shorts = active.filter(t => t.side === 'Short');
        const longWinRate = longs.length > 0 ? (longs.filter(t => t.pnl > 0).length / longs.length) * 100 : 0;
        const shortWinRate = shorts.length > 0 ? (shorts.filter(t => t.pnl > 0).length / shorts.length) * 100 : 0;

        // Best/worst single trade
        const bestTrade = active.reduce((best, t) => t.pnl > best.pnl ? t : best, active[0]);
        const worstTrade = active.reduce((worst, t) => t.pnl < worst.pnl ? t : worst, active[0]);

        // Avg trade duration (in minutes)
        const durations = active
            .map(t => {
                const entry = new Date(t.entry_execution_time || t.entry_time).getTime();
                const exit = new Date(t.exit_execution_time || t.exit_time).getTime();
                return (exit - entry) / 60000;
            })
            .filter(d => d > 0 && isFinite(d));
        const avgDuration = durations.length > 0 ? durations.reduce((s, d) => s + d, 0) / durations.length : 0;

        return {
            avgWin, avgLoss,
            avgPerDay, tradingDays,
            profitFactor,
            bestDow, worstDow,
            bestDate, worstDate,
            longs: longs.length, shorts: shorts.length, longWinRate, shortWinRate,
            bestTrade, worstTrade,
            avgDuration,
        };
    }, [trades]);

    if (!analytics) return null;

    return (
        <div className="glass-panel rounded-xl overflow-hidden">
            <div className="p-5 border-b border-gray-700/50 bg-gray-800/30">
                <button
                    onClick={() => setExpanded(!expanded)}
                    className="flex items-center gap-2 text-gray-400 hover:text-gray-200 transition-colors"
                    aria-expanded={expanded}
                >
                    {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    <h3 className="text-sm uppercase tracking-wider font-semibold">Trade Analytics</h3>
                </button>
            </div>

            {expanded && (
                <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0">
                    {/* Left column */}
                    <div>
                        <MetricRow label="Avg Win / Avg Loss">
                            <div className="flex items-center gap-2">
                                <PnlValue value={analytics.avgWin} />
                                <span className="text-gray-600">/</span>
                                <PnlValue value={analytics.avgLoss} />
                            </div>
                        </MetricRow>

                        <MetricRow label="Avg PnL / Trading Day">
                            <div className="flex items-center gap-2">
                                <PnlValue value={analytics.avgPerDay} prefix="$" />
                                <span className="text-gray-500 text-xs">({analytics.tradingDays} days)</span>
                            </div>
                        </MetricRow>

                        <MetricRow label="Profit Factor">
                            <span className={`font-bold ${analytics.profitFactor >= 1 ? 'text-green-400' : 'text-red-400'}`}>
                                {analytics.profitFactor === Infinity ? '∞' : analytics.profitFactor.toFixed(2)}
                            </span>
                        </MetricRow>

                        <MetricRow label="Best Day of Week">
                            <div className="flex items-center gap-2">
                                <span className="text-gray-300">{analytics.bestDow.day}</span>
                                <PnlValue value={analytics.bestDow.pnl} />
                            </div>
                        </MetricRow>

                        <MetricRow label="Worst Day of Week">
                            <div className="flex items-center gap-2">
                                <span className="text-gray-300">{analytics.worstDow.day}</span>
                                <PnlValue value={analytics.worstDow.pnl} />
                            </div>
                        </MetricRow>
                    </div>

                    {/* Right column */}
                    <div>
                        <MetricRow label="Best Trading Day">
                            <div className="flex items-center gap-2">
                                <span className="text-gray-300">{analytics.bestDate.date}</span>
                                <PnlValue value={analytics.bestDate.pnl} />
                            </div>
                        </MetricRow>

                        <MetricRow label="Worst Trading Day">
                            <div className="flex items-center gap-2">
                                <span className="text-gray-300">{analytics.worstDate.date}</span>
                                <PnlValue value={analytics.worstDate.pnl} />
                            </div>
                        </MetricRow>

                        <MetricRow label="Direction">
                            <div className="flex items-center gap-3">
                                <span className="flex items-center gap-1 text-green-400">
                                    <ArrowUp className="w-3 h-3" />
                                    {analytics.longs}
                                    <span className="text-gray-500 text-xs">({analytics.longWinRate.toFixed(0)}%)</span>
                                </span>
                                <span className="text-gray-600">/</span>
                                <span className="flex items-center gap-1 text-red-400">
                                    <ArrowDown className="w-3 h-3" />
                                    {analytics.shorts}
                                    <span className="text-gray-500 text-xs">({analytics.shortWinRate.toFixed(0)}%)</span>
                                </span>
                            </div>
                        </MetricRow>

                        <MetricRow label="Best Trade / Worst Trade">
                            <div className="flex items-center gap-2">
                                <PnlValue value={analytics.bestTrade.pnl} />
                                <span className="text-gray-600">/</span>
                                <PnlValue value={analytics.worstTrade.pnl} />
                            </div>
                        </MetricRow>

                        <MetricRow label="Avg Trade Duration">
                            <span className="text-gray-300">{formatDuration(analytics.avgDuration)}</span>
                        </MetricRow>
                    </div>
                </div>
            )}
        </div>
    );
}
