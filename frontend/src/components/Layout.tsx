import { Activity } from 'lucide-react';

interface LayoutProps {
    children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
    return (
        <div className="min-h-screen bg-[#0B0F19] text-gray-100 p-6 font-sans selection:bg-blue-500/30">
            <div className="max-w-[1600px] mx-auto">
                <header className="mb-8 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2.5 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl shadow-lg shadow-blue-900/20">
                            <Activity className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 bg-clip-text text-transparent">
                                Toini666 Backtester
                            </h1>
                            <div className="text-xs text-blue-400/60 font-medium tracking-widest uppercase">
                                Quantitative Engine
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="px-3 py-1 rounded-full bg-gray-800/50 border border-gray-700 text-xs text-gray-400 font-mono">
                            version 2.0
                        </div>
                    </div>
                </header>

                <main>
                    {children}
                </main>
            </div>
        </div>
    );
}
