import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { TrendingUp, Activity, Clock, DollarSign, RefreshCw } from 'lucide-react';
import { KpiCard } from './KpiCard';
import { EquityChart } from './EquityChart';
import { DailyPnlCalendar } from './DailyPnlCalendar';
import { TradesTable } from './TradesTable';
import { TradeAnalytics } from './TradeAnalytics';
import { SessionAnalytics } from './SessionAnalytics';
import { type BacktestResult, type BacktestMetrics, type BacktestMode, type MultiBacktestResult } from '../api';

interface DashboardProps {
    filteredResult: BacktestResult | null;
    /** Combined result for multi-asset / multi-strat modes */
    multiResult?: MultiBacktestResult | null;
    backtestMode?: BacktestMode;
    selectedSessions: string[];
    onSessionsChange: (sessions: string[]) => void;
    dataSource: string;
    initialEquity?: number;
    autoUpdate?: boolean;
    autoUpdateLoading?: boolean;
    previousMetrics?: BacktestMetrics | null;
}

function computeDelta(current: number, previous: number, suffix: string, higherIsBetter: boolean): { label: string; color: string } {
    const delta = current - previous;
    const sign = delta > 0 ? '+' : '';
    const isBetter = higherIsBetter ? delta > 0 : delta < 0;
    const color = delta === 0 ? 'text-gray-500' : isBetter ? 'text-green-400' : 'text-red-400';
    return { label: `${sign}${delta.toFixed(suffix === '' ? 0 : 2)}${suffix}`, color };
}

/** Mini metric row for the per-config breakdown in multi mode */
function ConfigMetricRow({
    label,
    metrics,
    initialEquity,
    slotColor,
    blockedCount,
}: {
    label: string;
    metrics: BacktestMetrics;
    initialEquity: number;
    slotColor: 'blue' | 'violet';
    blockedCount: number;
}) {
    const colorClass = slotColor === 'blue' ? 'text-blue-400 border-blue-500/20 bg-blue-500/5' : 'text-violet-400 border-violet-500/20 bg-violet-500/5';
    const returnColor = metrics.total_return >= 0 ? 'text-green-400' : 'text-red-400';
    return (
        <div className={`rounded-lg border p-4 ${colorClass}`}>
            <div className="flex items-center justify-between mb-3">
                <span className={`text-xs font-bold uppercase tracking-wider ${slotColor === 'blue' ? 'text-blue-400' : 'text-violet-400'}`}>
                    #{slotColor === 'blue' ? '1' : '2'} — {label}
                </span>
                {blockedCount > 0 && (
                    <span className="text-xs text-yellow-500/80 bg-yellow-500/10 border border-yellow-500/20 rounded px-2 py-0.5">
                        {blockedCount} blocked
                    </span>
                )}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div>
                    <div className="text-gray-500 uppercase tracking-wide mb-1">Return</div>
                    <div className={`font-mono font-bold ${returnColor}`}>{metrics.total_return.toFixed(2)}%</div>
                    <div className={`font-mono text-[11px] ${returnColor} opacity-60`}>
                        {metrics.total_return >= 0 ? '+' : '-'}${Math.abs(metrics.total_return / 100 * initialEquity).toFixed(2)}
                    </div>
                </div>
                <div>
                    <div className="text-gray-500 uppercase tracking-wide mb-1">Win Rate</div>
                    <div className="font-mono font-bold text-blue-400">{metrics.win_rate.toFixed(1)}%</div>
                </div>
                <div>
                    <div className="text-gray-500 uppercase tracking-wide mb-1">Trades</div>
                    <div className="font-mono font-bold text-orange-400">{metrics.total_trades}</div>
                </div>
                <div>
                    <div className="text-gray-500 uppercase tracking-wide mb-1">Max DD</div>
                    <div className="font-mono font-bold text-red-400">{metrics.max_drawdown.toFixed(2)}%</div>
                    <div className="font-mono text-[11px] text-red-400 opacity-60">
                        -${(metrics.max_drawdown / 100 * initialEquity).toFixed(2)}
                    </div>
                </div>
            </div>
        </div>
    );
}

export function Dashboard({
    filteredResult,
    multiResult = null,
    backtestMode = 'single',
    selectedSessions,
    onSessionsChange,
    dataSource,
    initialEquity,
    autoUpdate = false,
    autoUpdateLoading = false,
    previousMetrics = null,
}: DashboardProps) {

    const [chartView, setChartView] = useState<'equity' | 'calendar'>('equity');
    const kpiRef = useRef<HTMLDivElement>(null);
    const [showStickyMetrics, setShowStickyMetrics] = useState(false);

    const isMulti = backtestMode !== 'single';
    // Use multiResult when in multi mode, filteredResult otherwise
    const activeResult: (BacktestResult | MultiBacktestResult | null) = isMulti ? multiResult : filteredResult;
    const equity = initialEquity || 50000;

    useEffect(() => {
        if (!autoUpdate || !kpiRef.current) {
            setShowStickyMetrics(false);
            return;
        }
        const observer = new IntersectionObserver(
            ([entry]) => setShowStickyMetrics(!entry.isIntersecting),
            { threshold: 0 },
        );
        observer.observe(kpiRef.current);
        return () => observer.disconnect();
    }, [autoUpdate, filteredResult, multiResult]);

    if (!activeResult) {
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

    const { metrics, equity_curve, trades } = activeResult;
    const debugFile = !isMulti ? (filteredResult as BacktestResult)?.debug_file : null;
    const dailyLimitsHit = !isMulti ? (filteredResult as BacktestResult)?.daily_limits_hit : undefined;

    const returnDelta = previousMetrics ? computeDelta(metrics.total_return, previousMetrics.total_return, '%', true) : null;
    const winRateDelta = previousMetrics ? computeDelta(metrics.win_rate, previousMetrics.win_rate, '%', true) : null;
    const tradesDelta = previousMetrics ? computeDelta(metrics.total_trades, previousMetrics.total_trades, '', true) : null;
    const drawdownDelta = previousMetrics ? computeDelta(metrics.max_drawdown, previousMetrics.max_drawdown, '%', false) : null;

    return (
        <div className="space-y-6 animate-fadeIn pb-10" role="main" aria-label="Backtest results">

            {/* Sticky metrics bar for auto-update mode */}
            {autoUpdate && showStickyMetrics && createPortal(
                <div className="fixed top-0 left-0 right-0 z-50 bg-gray-900/95 backdrop-blur-md border-b border-gray-700/60 shadow-2xl">
                    <div className="max-w-screen-2xl mx-auto px-8 py-3.5 flex items-center gap-8">
                        <div className={`flex items-center gap-2 text-sm font-semibold shrink-0 ${autoUpdateLoading ? 'text-amber-400' : 'text-emerald-400'}`}>
                            <RefreshCw className={`w-4 h-4 ${autoUpdateLoading ? 'animate-spin' : ''}`} />
                            {autoUpdateLoading ? 'Updating...' : 'Auto-Update'}
                        </div>
                        <div className="flex items-baseline gap-10 flex-1 justify-center">
                            <div className="flex items-baseline gap-2">
                                <TrendingUp className={`w-4 h-4 self-center ${metrics.total_return >= 0 ? 'text-green-400' : 'text-red-400'}`} />
                                <span className="text-xs text-gray-500 uppercase tracking-wide">Return</span>
                                <span className={`text-lg font-bold font-mono ${metrics.total_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                    {metrics.total_return.toFixed(2)}%
                                </span>
                                {returnDelta && <span className={`text-xs font-mono ${returnDelta.color}`}>{returnDelta.label}</span>}
                            </div>
                            <div className="flex items-baseline gap-2">
                                <Activity className="w-4 h-4 self-center text-blue-400" />
                                <span className="text-xs text-gray-500 uppercase tracking-wide">Win Rate</span>
                                <span className="text-lg font-bold font-mono text-blue-400">{metrics.win_rate.toFixed(1)}%</span>
                                {winRateDelta && <span className={`text-xs font-mono ${winRateDelta.color}`}>{winRateDelta.label}</span>}
                            </div>
                            <div className="flex items-baseline gap-2">
                                <Clock className="w-4 h-4 self-center text-orange-400" />
                                <span className="text-xs text-gray-500 uppercase tracking-wide">Trades</span>
                                <span className="text-lg font-bold font-mono text-orange-400">{metrics.total_trades}</span>
                                {tradesDelta && <span className={`text-xs font-mono ${tradesDelta.color}`}>{tradesDelta.label}</span>}
                            </div>
                            <div className="flex items-baseline gap-2">
                                <DollarSign className="w-4 h-4 self-center text-red-400" />
                                <span className="text-xs text-gray-500 uppercase tracking-wide">Max DD</span>
                                <span className="text-lg font-bold font-mono text-red-400">{metrics.max_drawdown.toFixed(2)}%</span>
                                {drawdownDelta && <span className={`text-xs font-mono ${drawdownDelta.color}`}>{drawdownDelta.label}</span>}
                            </div>
                        </div>
                    </div>
                </div>,
                document.body,
            )}

            {debugFile && (
                <div className="glass-panel rounded-xl p-4 border border-cyan-800/40">
                    <div className="text-xs uppercase tracking-wider text-cyan-400 font-semibold mb-1">Debug Export</div>
                    <div className="text-sm text-gray-300 font-mono break-all">{debugFile}</div>
                </div>
            )}

            {/* Multi mode header */}
            {isMulti && (
                <div className="flex items-center gap-3">
                    <span className={`text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-md border ${
                        backtestMode === 'multi_asset'
                            ? 'text-violet-400 border-violet-500/30 bg-violet-500/10'
                            : 'text-fuchsia-400 border-fuchsia-500/30 bg-fuchsia-500/10'
                    }`}>
                        {backtestMode === 'multi_asset' ? 'Multi-Asset' : 'Multi-Strategy'}
                    </span>
                    <span className="text-xs text-gray-500">Combined results — compte unique, deux stratégies/assets en parallèle</span>
                </div>
            )}

            {/* Combined KPI Cards */}
            <div ref={kpiRef} className="grid grid-cols-2 md:grid-cols-4 gap-4" role="region" aria-label="Key performance indicators">
                <KpiCard
                    label={isMulti ? 'Combined Return' : 'Total Return'}
                    value={`${metrics.total_return.toFixed(2)}%`}
                    icon={TrendingUp}
                    color={metrics.total_return >= 0 ? 'text-green-400' : 'text-red-400'}
                    subValue={`${metrics.total_return >= 0 ? '+' : '-'}$${Math.abs(metrics.total_return / 100 * equity).toFixed(2)}`}
                    subColor={metrics.total_return >= 0 ? 'text-green-400' : 'text-red-400'}
                    deltaLabel={returnDelta?.label}
                    deltaColor={returnDelta?.color}
                />
                <KpiCard
                    label="Win Rate"
                    value={`${metrics.win_rate.toFixed(2)}%`}
                    icon={Activity}
                    color="text-blue-400"
                    deltaLabel={winRateDelta?.label}
                    deltaColor={winRateDelta?.color}
                />
                <KpiCard
                    label="Total Trades"
                    value={metrics.total_trades.toString()}
                    icon={Clock}
                    color="text-orange-400"
                    deltaLabel={tradesDelta?.label}
                    deltaColor="text-gray-400"
                />
                <KpiCard
                    label="Max Drawdown"
                    value={`${metrics.max_drawdown.toFixed(2)}%`}
                    icon={DollarSign}
                    color="text-red-400"
                    subValue={`-$${(metrics.max_drawdown / 100 * equity).toFixed(2)}`}
                    subColor="text-red-400"
                    deltaLabel={drawdownDelta?.label}
                    deltaColor={drawdownDelta?.color}
                />
            </div>

            {/* Per-config breakdown (multi mode only) */}
            {isMulti && multiResult && multiResult.config_results.length === 2 && (
                <div className="space-y-3">
                    <h3 className="text-xs uppercase tracking-wider text-gray-500 font-semibold">Breakdown par configuration</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {multiResult.config_results.map((cr, i) => (
                            <ConfigMetricRow
                                key={i}
                                label={cr.label}
                                metrics={cr.metrics}
                                initialEquity={equity}
                                slotColor={i === 0 ? 'blue' : 'violet'}
                                blockedCount={cr.blocked_count}
                            />
                        ))}
                    </div>
                </div>
            )}

            {/* Chart / Calendar toggle */}
            <div>
                <div className="flex items-center gap-1 mb-3">
                    <div className="inline-flex rounded-lg bg-gray-800/50 p-0.5 border border-gray-700/50">
                        <button
                            onClick={() => setChartView('equity')}
                            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                                chartView === 'equity' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-gray-300'
                            }`}
                        >
                            Equity Curve
                        </button>
                        <button
                            onClick={() => setChartView('calendar')}
                            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                                chartView === 'calendar' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-gray-300'
                            }`}
                        >
                            Daily PnL Summary
                        </button>
                    </div>
                </div>
                {chartView === 'equity' ? (
                    <EquityChart data={equity_curve} />
                ) : (
                    <DailyPnlCalendar trades={trades} dailyLimitsHit={dailyLimitsHit} />
                )}
            </div>

            {/* Trade History */}
            <TradesTable
                trades={trades}
                selectedSessions={selectedSessions}
                onSessionsChange={onSessionsChange}
                multiMode={isMulti}
            />

            {/* Trade Analytics */}
            <TradeAnalytics trades={trades} initialEquity={initialEquity} />

            {/* Session Analytics */}
            <SessionAnalytics trades={trades} initialEquity={initialEquity} multiMode={isMulti} />
        </div>
    );
}
