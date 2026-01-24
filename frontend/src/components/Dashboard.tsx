import { TrendingUp, Activity, Clock, DollarSign } from 'lucide-react';
import { KpiCard } from './KpiCard';
import { EquityChart } from './EquityChart';
import { TradesTable } from './TradesTable';

interface SessionStat {
    session: string;
    total_trades: number;
    win_rate: number;
    total_return: number;
}

interface DashboardProps {
    filteredResult: any; // Using any for brevity if types overlap, but ideally BacktestResult
    selectedSessions: string[];
    toggleSession: (s: string) => void;
    dataSource: string;
    initialEquity?: number;
    sessionStats: SessionStat[];
}

export function Dashboard({ filteredResult, selectedSessions, toggleSession, dataSource, initialEquity, sessionStats }: DashboardProps) {

    if (!filteredResult) {
        return (
            <div className="glass-panel border-dashed rounded-xl h-full flex flex-col items-center justify-center text-gray-500 min-h-[500px]">
                <Activity className="w-20 h-20 mb-6 opacity-10 animate-pulse" />
                <p className="text-2xl font-light text-gray-400">Ready to Simulate</p>
                <p className="text-sm mt-3 opacity-60 max-w-md text-center">
                    Configure your strategy settings in the sidebar and press "Run Backtest" to see results.
                </p>
                <div className="mt-8 flex gap-4 text-xs font-mono opacity-50">
                    <span className="bg-gray-800 px-3 py-1 rounded border border-gray-700">Source: {dataSource}</span>
                    {initialEquity && <span className="bg-gray-800 px-3 py-1 rounded border border-gray-700">Equity: ${initialEquity}</span>}
                </div>
            </div>
        );
    }

    const { metrics, equity_curve, trades } = filteredResult;

    return (
        <div className="space-y-6 animate-fadeIn pb-10">
            {/* Session Filters */}
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex gap-4">
                    {['Asia', 'UK', 'US'].map(sess => (
                        <label key={sess} className="flex items-center space-x-2 text-gray-300 cursor-pointer select-none group">
                            <div className="relative">
                                <input
                                    type="checkbox"
                                    checked={selectedSessions.includes(sess)}
                                    onChange={() => toggleSession(sess)}
                                    className="peer sr-only"
                                />
                                <div className="w-5 h-5 border-2 border-gray-600 rounded bg-gray-900 group-hover:border-gray-500 peer-checked:bg-blue-600 peer-checked:border-blue-600 transition-all flex items-center justify-center">
                                    <svg className="w-3 h-3 text-white hidden peer-checked:block" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                    </svg>
                                </div>
                            </div>
                            <span className="font-medium">{sess}</span>
                        </label>
                    ))}
                </div>
                <div className="text-gray-500 text-xs font-mono bg-gray-800/50 px-3 py-1.5 rounded-full border border-gray-800">
                    Showing {trades.length} trades
                </div>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard
                    label="Total Return"
                    value={`${metrics.total_return.toFixed(2)}%`}
                    icon={TrendingUp}
                    color={metrics.total_return >= 0 ? "text-green-400" : "text-red-400"}
                />
                <KpiCard
                    label="Win Rate"
                    value={`${metrics.win_rate.toFixed(2)}%`}
                    icon={Activity}
                    color="text-blue-400"
                />
                <KpiCard
                    label="Total Trades"
                    value={metrics.total_trades}
                    icon={Clock}
                    color="text-orange-400"
                />
                <KpiCard
                    label="Max Drawdown"
                    value={`${metrics.max_drawdown.toFixed(2)}%`}
                    icon={DollarSign}
                    color="text-red-400"
                />
            </div>

            {/* Chart */}
            <EquityChart data={equity_curve} />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Trades Table */}
                <div className="lg:col-span-2 h-[400px]">
                    <TradesTable trades={trades} />
                </div>

                {/* Session Summary Table */}
                <div className="glass-panel rounded-xl overflow-hidden flex flex-col h-[400px]">
                    <div className="p-5 border-b border-gray-700/50 bg-gray-800/30">
                        <h3 className="text-gray-400 text-sm uppercase tracking-wider font-semibold">Session Analytics</h3>
                    </div>
                    <div className="overflow-auto flex-1">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-gray-900/50 text-gray-400">
                                <tr>
                                    <th className="p-4 font-medium">Session</th>
                                    <th className="p-4 font-medium text-right">Win %</th>
                                    <th className="p-4 font-medium text-right">Return</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-700/30">
                                {sessionStats.map((stat) => (
                                    <tr key={stat.session} className="hover:bg-white/5 transition-colors">
                                        <td className="p-4 font-bold text-gray-300">{stat.session}</td>
                                        <td className="p-4 text-right">{stat.win_rate.toFixed(0)}%</td>
                                        <td className={`p-4 text-right font-mono font-bold ${stat.total_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                            {stat.total_return >= 0 ? '+' : ''}{stat.total_return.toFixed(2)}%
                                        </td>
                                    </tr>
                                ))}
                                {sessionStats.length === 0 && (
                                    <tr><td colSpan={3} className="p-4 text-center text-gray-500">No session data</td></tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}
