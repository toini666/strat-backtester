import { useState } from 'react';
import { TrendingUp, Activity, Clock, DollarSign } from 'lucide-react';
import { KpiCard } from './KpiCard';
import { EquityChart } from './EquityChart';
import { DailyPnlCalendar } from './DailyPnlCalendar';
import { TradesTable } from './TradesTable';
import { TradeAnalytics } from './TradeAnalytics';
import { SessionAnalytics } from './SessionAnalytics';
import { type BacktestResult } from '../api';

interface DashboardProps {
    filteredResult: BacktestResult | null;
    selectedSessions: string[];
    onSessionsChange: (sessions: string[]) => void;
    dataSource: string;
    initialEquity?: number;
}

export function Dashboard({
    filteredResult,
    selectedSessions,
    onSessionsChange,
    dataSource,
    initialEquity,
}: DashboardProps) {

    if (!filteredResult) {
        return (
            <div
                className="glass-panel border-dashed rounded-xl h-full flex flex-col items-center justify-center text-gray-500 min-h-[500px]"
                role="region"
                aria-label="Backtest results placeholder"
            >
                <Activity className="w-20 h-20 mb-6 opacity-10 animate-pulse" aria-hidden="true" />
                <p className="text-2xl font-light text-gray-400">Ready to Simulate</p>
                <p className="text-sm mt-3 opacity-60 max-w-md text-center">
                    Configure the backtest blocks above and press "Run Backtest" to see results.
                </p>
                <div className="mt-8 flex gap-4 text-xs font-mono opacity-50">
                    <span className="bg-gray-800 px-3 py-1 rounded border border-gray-700">Source: {dataSource}</span>
                    {initialEquity && <span className="bg-gray-800 px-3 py-1 rounded border border-gray-700">Equity: ${initialEquity.toLocaleString()}</span>}
                </div>
            </div>
        );
    }

    const { metrics, equity_curve, trades } = filteredResult;
    const [chartView, setChartView] = useState<'equity' | 'calendar'>('equity');

    return (
        <div className="space-y-6 animate-fadeIn pb-10" role="main" aria-label="Backtest results">

            {filteredResult.debug_file && (
                <div className="glass-panel rounded-xl p-4 border border-cyan-800/40">
                    <div className="text-xs uppercase tracking-wider text-cyan-400 font-semibold mb-1">Debug Export</div>
                    <div className="text-sm text-gray-300">
                        <span className="font-mono break-all">{filteredResult.debug_file}</span>
                    </div>
                </div>
            )}

            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4" role="region" aria-label="Key performance indicators">
                <KpiCard
                    label="Total Return"
                    value={`${metrics.total_return.toFixed(2)}%`}
                    icon={TrendingUp}
                    color={metrics.total_return >= 0 ? "text-green-400" : "text-red-400"}
                    subValue={`${metrics.total_return >= 0 ? '+' : '-'}$${Math.abs(metrics.total_return / 100 * (initialEquity || 50000)).toFixed(2)}`}
                    subColor={metrics.total_return >= 0 ? "text-green-400" : "text-red-400"}
                />
                <KpiCard
                    label="Win Rate"
                    value={`${metrics.win_rate.toFixed(2)}%`}
                    icon={Activity}
                    color="text-blue-400"
                />
                <KpiCard
                    label="Total Trades"
                    value={metrics.total_trades.toString()}
                    icon={Clock}
                    color="text-orange-400"
                />
                <KpiCard
                    label="Max Drawdown"
                    value={`${metrics.max_drawdown.toFixed(2)}%`}
                    icon={DollarSign}
                    color="text-red-400"
                    subValue={`-$${(metrics.max_drawdown / 100 * (initialEquity || 50000)).toFixed(2)}`}
                    subColor="text-red-400"
                />
            </div>

            {/* Chart / Calendar toggle */}
            <div>
                <div className="flex items-center gap-1 mb-3">
                    <div className="inline-flex rounded-lg bg-gray-800/50 p-0.5 border border-gray-700/50">
                        <button
                            onClick={() => setChartView('equity')}
                            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                                chartView === 'equity'
                                    ? 'bg-blue-600 text-white shadow'
                                    : 'text-gray-400 hover:text-gray-300'
                            }`}
                        >
                            Equity Curve
                        </button>
                        <button
                            onClick={() => setChartView('calendar')}
                            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                                chartView === 'calendar'
                                    ? 'bg-blue-600 text-white shadow'
                                    : 'text-gray-400 hover:text-gray-300'
                            }`}
                        >
                            Daily PnL Summary
                        </button>
                    </div>
                </div>
                {chartView === 'equity' ? (
                    <EquityChart data={equity_curve} />
                ) : (
                    <DailyPnlCalendar trades={trades} dailyLimitsHit={filteredResult.daily_limits_hit} />
                )}
            </div>

            {/* Trade History — full width, no fixed height */}
            <TradesTable
                trades={trades}
                selectedSessions={selectedSessions}
                onSessionsChange={onSessionsChange}
            />

            {/* Trade Analytics — collapsed by default */}
            <TradeAnalytics trades={trades} initialEquity={initialEquity} />

            {/* Session Analytics — full width, hourly breakdown */}
            <SessionAnalytics trades={trades} initialEquity={initialEquity} />
        </div>
    );
}
