import { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { type Trade } from '../api';

interface DailyPnlCalendarProps {
    trades: Trade[];
    dailyLimitsHit?: Record<string, string>;  // date (YYYY-MM-DD) -> "win"|"loss"
}

interface DayData {
    pnl: number;
    tradeCount: number;
}

const WEEKDAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];

// Cached formatters
const brusselsDateFormatter = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Europe/Brussels',
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    weekday: 'short',
});

const brusselsHourFormatter = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Europe/Brussels',
    hour: 'numeric',
    day: 'numeric',
    hour12: false,
});

const easternHourFormatter = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    hour: 'numeric',
    day: 'numeric',
    hour12: false,
});

/**
 * Safely parse a trade timestamp into a Date.
 * Pandas Timestamps can be "2026-01-15 00:07:00+01:00" (space-separated)
 * which some JS engines don't parse. We normalize to ISO 8601 (T-separated).
 */
function parseTimestamp(ts: string): Date {
    const normalized = ts.replace(/^(\d{4}-\d{2}-\d{2}) (\d{2})/, '$1T$2');
    return new Date(normalized);
}

/**
 * Detect the DST market hour offset for a given timestamp.
 *
 * CME futures follow US/Eastern time. When Brussels and US/Eastern are in the
 * same DST state, the difference is 6h and sessions start at midnight Brussels.
 * During the ~3-week spring window and ~1-week autumn window, the difference
 * drops to 5h — sessions start at 23:00 Brussels the previous calendar day.
 *
 * Returns 0 (normal) or -1 (shifted — sessions start 1h earlier).
 */
function getMarketHourOffset(d: Date): number {
    const bxlParts = brusselsHourFormatter.formatToParts(d);
    const etParts = easternHourFormatter.formatToParts(d);

    const bxlHour = Number(bxlParts.find(p => p.type === 'hour')?.value);
    const bxlDay = Number(bxlParts.find(p => p.type === 'day')?.value);
    const etHour = Number(etParts.find(p => p.type === 'hour')?.value);
    const etDay = Number(etParts.find(p => p.type === 'day')?.value);

    let diff = (bxlHour - etHour) + (bxlDay - etDay) * 24;
    // Normalize to 0-23 range
    diff = ((diff % 24) + 24) % 24;

    // diff=6 → standard (offset=0), diff=5 → shifted (offset=-1)
    return diff === 5 ? -1 : 0;
}

function toDateKey(year: number, month: number, day: number): string {
    return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

function extractBrusselsDate(d: Date): { year: number; month: number; day: number; dow: string } {
    const parts = brusselsDateFormatter.formatToParts(d);
    return {
        year: Number(parts.find(p => p.type === 'year')?.value),
        month: Number(parts.find(p => p.type === 'month')?.value),
        day: Number(parts.find(p => p.type === 'day')?.value),
        dow: parts.find(p => p.type === 'weekday')?.value || '',
    };
}

/**
 * Convert a trade timestamp to a Brussels "session date" key (YYYY-MM-DD).
 *
 * During DST-shifted periods (sessions start at 23:00 Brussels), trades
 * between 23:00-23:59 Brussels belong to the next calendar day's session.
 * This is achieved by shifting the timestamp by -offset hours (i.e. +1h when
 * offset=-1) before extracting the Brussels date — same reference-frame logic
 * as the simulator.
 *
 * Weekend dates (Sat/Sun) are shifted to the following Monday.
 */
function toSessionDateKey(dateStr: string): string {
    const d = parseTimestamp(dateStr);
    if (Number.isNaN(d.getTime())) return '';

    // Apply DST market offset: shift to reference frame
    const offset = getMarketHourOffset(d);
    const refDate = offset === 0 ? d : new Date(d.getTime() + (-offset) * 3600000);

    const p = extractBrusselsDate(refDate);

    if (p.dow === 'Sat') {
        const shifted = new Date(refDate.getTime() + 2 * 86400000);
        const sp = extractBrusselsDate(shifted);
        return toDateKey(sp.year, sp.month, sp.day);
    }
    if (p.dow === 'Sun') {
        const shifted = new Date(refDate.getTime() + 86400000);
        const sp = extractBrusselsDate(shifted);
        return toDateKey(sp.year, sp.month, sp.day);
    }
    return toDateKey(p.year, p.month, p.day);
}

/** Build weeks of weekdays only (Mon-Fri) for a given month. */
function getMonthWeeks(year: number, month: number): (Date | null)[][] {
    const weeks: (Date | null)[][] = [];
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    let currentWeek: (Date | null)[] = [];

    const firstDay = new Date(year, month, 1);
    let firstDow = (firstDay.getDay() + 6) % 7; // 0=Mon..6=Sun
    if (firstDow > 4) firstDow = 0;

    for (let i = 0; i < firstDow; i++) {
        currentWeek.push(null);
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const date = new Date(year, month, day);
        const dow = (date.getDay() + 6) % 7;
        if (dow >= 5) continue;

        currentWeek.push(date);
        if (currentWeek.length === 5) {
            weeks.push(currentWeek);
            currentWeek = [];
        }
    }

    if (currentWeek.length > 0) {
        while (currentWeek.length < 5) {
            currentWeek.push(null);
        }
        weeks.push(currentWeek);
    }

    return weeks;
}

function formatPnl(value: number): string {
    const sign = value >= 0 ? '+' : '-';
    return `${sign}$${Math.abs(value).toFixed(2)}`;
}

function dateToKey(d: Date): string {
    return toDateKey(d.getFullYear(), d.getMonth() + 1, d.getDate());
}

export function DailyPnlCalendar({ trades, dailyLimitsHit }: DailyPnlCalendarProps) {
    const activeTrades = useMemo(() => trades.filter(t => !t.excluded), [trades]);

    // Aggregate PNL by Brussels session date (DST-aware, weekend → Monday)
    const dailyData = useMemo(() => {
        const map: Record<string, DayData> = {};
        for (const trade of activeTrades) {
            const entryTime = trade.entry_time;
            if (!entryTime) continue;
            const dateKey = toSessionDateKey(entryTime);
            if (!dateKey) continue;
            if (!map[dateKey]) {
                map[dateKey] = { pnl: 0, tradeCount: 0 };
            }
            map[dateKey].pnl += trade.pnl;
            map[dateKey].tradeCount += 1;
        }
        return map;
    }, [activeTrades]);

    const initialDate = useMemo(() => {
        if (activeTrades.length === 0) return new Date();
        const first = activeTrades[0].entry_time;
        if (!first) return new Date();
        return parseTimestamp(first);
    }, [activeTrades]);

    const [currentYear, setCurrentYear] = useState(initialDate.getFullYear());
    const [currentMonth, setCurrentMonth] = useState(initialDate.getMonth());

    const weeks = useMemo(() => getMonthWeeks(currentYear, currentMonth), [currentYear, currentMonth]);

    const weeklyTotals = useMemo(() => {
        return weeks.map(week => {
            let pnl = 0;
            let tradeCount = 0;
            for (const day of week) {
                if (!day) continue;
                const data = dailyData[dateToKey(day)];
                if (data) {
                    pnl += data.pnl;
                    tradeCount += data.tradeCount;
                }
            }
            return { pnl, tradeCount };
        });
    }, [weeks, dailyData]);

    const monthlyTotal = useMemo(() => {
        let pnl = 0;
        let tradeCount = 0;
        for (const wt of weeklyTotals) {
            pnl += wt.pnl;
            tradeCount += wt.tradeCount;
        }
        return { pnl, tradeCount };
    }, [weeklyTotals]);

    const prevMonth = () => {
        if (currentMonth === 0) {
            setCurrentYear(y => y - 1);
            setCurrentMonth(11);
        } else {
            setCurrentMonth(m => m - 1);
        }
    };

    const nextMonth = () => {
        if (currentMonth === 11) {
            setCurrentYear(y => y + 1);
            setCurrentMonth(0);
        } else {
            setCurrentMonth(m => m + 1);
        }
    };

    const monthLabel = new Date(currentYear, currentMonth).toLocaleDateString('en-US', {
        month: 'long',
        year: 'numeric',
    });

    return (
        <div className="glass-panel rounded-xl p-5 flex flex-col" style={{ minHeight: '400px' }}>
            {/* Header */}
            <div className="flex items-center justify-between mb-1">
                <button onClick={prevMonth} className="p-1.5 rounded-lg hover:bg-gray-700/50 text-gray-400 hover:text-gray-200 transition-colors">
                    <ChevronLeft className="w-5 h-5" />
                </button>
                <h3 className="text-gray-300 text-sm uppercase tracking-wider font-semibold">{monthLabel}</h3>
                <button onClick={nextMonth} className="p-1.5 rounded-lg hover:bg-gray-700/50 text-gray-400 hover:text-gray-200 transition-colors">
                    <ChevronRight className="w-5 h-5" />
                </button>
            </div>

            {/* Monthly summary */}
            <div className="text-center mb-4">
                {monthlyTotal.tradeCount > 0 ? (
                    <div className="flex items-center justify-center gap-3">
                        <span className={`text-lg font-mono font-bold ${monthlyTotal.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {formatPnl(monthlyTotal.pnl)}
                        </span>
                        <span className="text-xs text-gray-500">
                            {monthlyTotal.tradeCount} trade{monthlyTotal.tradeCount > 1 ? 's' : ''}
                        </span>
                    </div>
                ) : (
                    <span className="text-xs text-gray-600">No trades this month</span>
                )}
            </div>

            {/* Calendar grid */}
            <div className="flex-1">
                <table className="w-full border-collapse table-fixed">
                    <thead>
                        <tr>
                            {WEEKDAY_LABELS.map(d => (
                                <th key={d} className="text-xs text-gray-500 font-medium pb-2 text-center">{d}</th>
                            ))}
                            <th className="text-xs text-gray-500 font-medium pb-2 text-center w-[14%]">Week</th>
                        </tr>
                    </thead>
                    <tbody>
                        {weeks.map((week, wi) => (
                            <tr key={wi}>
                                {week.map((day, di) => {
                                    if (!day) {
                                        return <td key={di} className="border border-gray-800/30 p-2 h-[72px]" />;
                                    }
                                    const key = dateToKey(day);
                                    const data = dailyData[key];
                                    const limitType = dailyLimitsHit?.[key];

                                    return (
                                        <td
                                            key={di}
                                            className={`border border-gray-800/30 p-2 h-[72px] text-center align-middle transition-colors ${
                                                limitType === 'win'
                                                    ? 'bg-emerald-900/15'
                                                    : limitType === 'loss'
                                                        ? 'bg-red-900/15'
                                                        : ''
                                            } ${data ? 'hover:bg-gray-700/20' : ''}`}
                                            title={limitType === 'win' ? 'Daily win limit reached' : limitType === 'loss' ? 'Daily loss limit reached' : undefined}
                                        >
                                            <div className="flex items-center justify-center gap-1 mb-0.5">
                                                <span className="text-[11px] text-gray-500">{day.getDate()}</span>
                                                {limitType && (
                                                    <span className={`text-[9px] font-bold uppercase px-1 rounded ${
                                                        limitType === 'win'
                                                            ? 'bg-emerald-800/40 text-emerald-400'
                                                            : 'bg-red-800/40 text-red-400'
                                                    }`}>
                                                        {limitType === 'win' ? 'DW' : 'DL'}
                                                    </span>
                                                )}
                                            </div>
                                            {data && (
                                                <div>
                                                    <div className={`text-sm font-mono font-bold leading-tight ${data.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                        {formatPnl(data.pnl)}
                                                    </div>
                                                    <div className="text-[10px] text-gray-500 mt-0.5">
                                                        {data.tradeCount} trade{data.tradeCount > 1 ? 's' : ''}
                                                    </div>
                                                </div>
                                            )}
                                        </td>
                                    );
                                })}
                                {/* Weekly total */}
                                <td className="border border-gray-800/30 p-2 h-[72px] align-middle text-center">
                                    {weeklyTotals[wi].tradeCount > 0 && (
                                        <div>
                                            <div className={`text-sm font-mono font-bold ${weeklyTotals[wi].pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                {formatPnl(weeklyTotals[wi].pnl)}
                                            </div>
                                            <div className="text-[10px] text-gray-500 mt-0.5">
                                                {weeklyTotals[wi].tradeCount} trade{weeklyTotals[wi].tradeCount > 1 ? 's' : ''}
                                            </div>
                                        </div>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
