import { Fragment } from 'react';
import { ArrowDown, ArrowUp } from 'lucide-react';
import { type Trade, type TradeLeg } from '../api';

interface TradesTableProps {
    trades: Trade[];
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

export function TradesTable({ trades }: TradesTableProps) {
    return (
        <div className="glass-panel rounded-xl overflow-hidden flex flex-col h-full">
            <div className="p-5 border-b border-gray-700/50 bg-gray-800/30">
                <h3 className="text-gray-400 text-sm uppercase tracking-wider font-semibold">Trade History</h3>
            </div>

            <div className="overflow-auto flex-1">
                <table className="w-full text-left text-sm whitespace-nowrap">
                    <thead className="bg-gray-900/80 backdrop-blur sticky top-0 z-10 text-gray-400">
                        <tr>
                            <th className="p-4 font-medium sticky top-0 bg-gray-900/80">Entry Bar</th>
                            <th className="p-4 font-medium sticky top-0 bg-gray-900/80">Exit Bar</th>
                            <th className="p-4 font-medium sticky top-0 bg-gray-900/80">Session</th>
                            <th className="p-4 font-medium sticky top-0 bg-gray-900/80">Side</th>
                            <th className="p-4 font-medium text-right sticky top-0 bg-gray-900/80">Entry</th>
                            <th className="p-4 font-medium text-right sticky top-0 bg-gray-900/80">Exit</th>
                            <th className="p-4 font-medium text-right sticky top-0 bg-gray-900/80">Size</th>
                            <th className="p-4 font-medium sticky top-0 bg-gray-900/80">Status</th>
                            <th className="p-4 font-medium text-right sticky top-0 bg-gray-900/80">Net PnL</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700/30">
                        {trades.map((trade, index) => {
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
                {trades.length === 0 && (
                    <div className="p-12 text-center text-gray-500 flex flex-col items-center justify-center">
                        <p>No trades recorded</p>
                    </div>
                )}
            </div>
        </div>
    );
}
