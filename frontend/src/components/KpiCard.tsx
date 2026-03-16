import { type LucideIcon } from 'lucide-react';

interface KpiCardProps {
    label: string;
    value: string | number;
    icon: LucideIcon;
    color?: string;
    subValue?: string;
    subColor?: string;
}

export function KpiCard({ label, value, icon: Icon, color, subValue, subColor }: KpiCardProps) {
    const iconColorClass = color || 'text-gray-400';

    return (
        <div className="glass-panel rounded-xl p-5 flex items-center gap-4 transition-transform hover:scale-[1.02] duration-200">
            <div className={`p-3 rounded-lg bg-gray-800/50 ${iconColorClass} bg-opacity-10`}>
                <Icon className={`w-6 h-6 ${iconColorClass}`} />
            </div>
            <div>
                <div className="text-xs text-gray-400 uppercase tracking-wider mb-1 font-medium">{label}</div>
                <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold font-mono text-gray-100">{value}</span>
                    {subValue && (
                        <span className={`text-sm font-mono font-semibold ${subColor || 'text-gray-400'}`}>
                            ({subValue})
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}
