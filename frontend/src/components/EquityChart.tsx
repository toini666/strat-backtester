import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer
} from 'recharts';

interface EquityPoint {
    time: string;
    value: number;
}

interface EquityChartProps {
    data: EquityPoint[];
}

export function EquityChart({ data }: EquityChartProps) {
    return (
        <div className="glass-panel rounded-xl p-5 h-[400px] flex flex-col">
            <h3 className="text-gray-400 text-sm uppercase tracking-wider mb-4 font-semibold">Equity Curve</h3>
            <div className="flex-1 w-full min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.5} />
                        <XAxis
                            dataKey="time"
                            stroke="#9CA3AF"
                            tick={{ fontSize: 12 }}
                            tickMargin={10}
                            minTickGap={30}
                        />
                        <YAxis
                            stroke="#9CA3AF"
                            domain={['auto', 'auto']}
                            tick={{ fontSize: 12 }}
                            tickFormatter={(value) => `$${value.toLocaleString()}`}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: '#111827',
                                border: '1px solid #374151',
                                borderRadius: '0.5rem',
                                color: '#fff',
                                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)'
                            }}
                            itemStyle={{ color: '#60A5FA' }}
                            labelStyle={{ color: '#9CA3AF', marginBottom: '0.25rem' }}
                            formatter={(value: number | undefined) => [`$${(value ?? 0).toFixed(2)}`, 'Equity']}
                        />
                        <Line
                            type="monotone"
                            dataKey="value"
                            stroke="#3B82F6"
                            strokeWidth={2}
                            dot={false}
                            activeDot={{ r: 6, fill: '#3B82F6', stroke: '#1F2937', strokeWidth: 2 }}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
