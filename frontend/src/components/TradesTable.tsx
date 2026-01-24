import { ArrowDown, ArrowUp } from 'lucide-react';

interface Trade {
    entry_time: string;
    session: string;
    side: string;
    entry_price: number;
    exit_price: number;
    size: number;
    gross_pnl: number;
    fees: number;
    pnl: number;
    exit_time?: string;
}

interface TradesTableProps {
    trades: Trade[];
}

export function TradesTable({ trades }: TradesTableProps) {
    return (
        <div className="glass-panel rounded-xl overflow-hidden flex flex-col h-full max-h-[500px]">
            <div className="p-5 border-b border-gray-700/50 bg-gray-800/30">
                <h3 className="text-gray-400 text-sm uppercase tracking-wider font-semibold">Trade History</h3>
            </div>

            <div className="overflow-auto flex-1">
                <table className="w-full text-left text-sm whitespace-nowrap">
                    <thead className="bg-gray-900/80 backdrop-blur sticky top-0 z-10 text-gray-400">
                        <tr>
                            <th className="p-4 font-medium sticky top-0 bg-gray-900/80">Entry Time</th>
                            <th className="p-4 font-medium sticky top-0 bg-gray-900/80">Session</th>
                            <th className="p-4 font-medium sticky top-0 bg-gray-900/80">Side</th>
                            <th className="p-4 font-medium text-right sticky top-0 bg-gray-900/80">Entry</th>
                            <th className="p-4 font-medium text-right sticky top-0 bg-gray-900/80">Exit</th>
                            <th className="p-4 font-medium text-right sticky top-0 bg-gray-900/80">Size</th>
                            <th className="p-4 font-medium text-right sticky top-0 bg-gray-900/80">Net PnL</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700/30">
                        {trades.map((trade, i) => (
                            <tr key={i} className="hover:bg-white/5 transition-colors">
                                <td className="p-4 text-gray-400 font-mono text-xs">
                                    {new Date(trade.entry_time).toLocaleString()}
                                </td>
                                <td className="p-4">
                                    <span className={`px-2 py-1 rounded-md text-xs font-bold border ${trade.session === 'Asia' ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' :
                                            trade.session === 'UK' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                                                trade.session === 'US' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' :
                                                    'bg-gray-600/10 text-gray-400 border-gray-600/20'
                                        }`}>
                                        {trade.session}
                                    </span>
                                </td>
                                <td className="p-4">
                                    <span className={`flex items-center gap-1 w-fit px-2 py-1 rounded-md text-xs font-bold border ${trade.side === 'Long'
                                            ? 'bg-green-500/10 text-green-400 border-green-500/20'
                                            : 'bg-red-500/10 text-red-400 border-red-500/20'
                                        }`}>
                                        {trade.side === 'Long' ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
                                        {trade.side}
                                    </span>
                                </td>
                                <td className="p-4 text-right font-mono text-gray-300">{trade.entry_price.toFixed(2)}</td>
                                <td className="p-4 text-right font-mono text-gray-300">{trade.exit_price.toFixed(2)}</td>
                                <td className="p-4 text-right font-mono text-gray-500">{trade.size?.toFixed(0) || '1'}</td>

                                <td className={`p-4 text-right font-mono font-bold ${trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                    {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                                </td>
                            </tr>
                        ))}
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
