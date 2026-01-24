import axios, { AxiosError } from 'axios';

// Use environment variable or fallback to localhost
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

// Configure axios instance with timeout and error handling
const apiClient = axios.create({
    baseURL: API_URL,
    timeout: 120000, // 2 minutes timeout for backtests
    headers: {
        'Content-Type': 'application/json',
    },
});

// Response interceptor for better error handling
apiClient.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
        if (error.code === 'ECONNABORTED') {
            throw new Error('Request timeout - the server took too long to respond');
        }
        if (!error.response) {
            throw new Error('Network error - please check your connection and ensure the backend is running');
        }
        // Re-throw with better error message
        const detail = (error.response.data as { detail?: string })?.detail;
        if (detail) {
            throw new Error(detail);
        }
        throw error;
    }
);

export interface Strategy {
    name: string;
    description: string;
    default_params: Record<string, number | string | boolean>;
}

export interface Contract {
    id: string;
    name: string;
    description: string;
    tick_size?: number;
    tick_value?: number;
}

export interface Trade {
    entry_time: string;
    exit_time: string;
    side: string;
    entry_price: number;
    exit_price: number;
    pnl: number;
    gross_pnl: number;
    fees: number;
    size: number;
    pnl_pct: number;
    status: string;
    session: string;
}

export interface BacktestMetrics {
    total_return: number;
    win_rate: number;
    total_trades: number;
    max_drawdown: number;
    sharpe_ratio: number;
}

export interface EquityPoint {
    time: string;
    value: number;
}

export interface BacktestResult {
    metrics: BacktestMetrics;
    trades: Trade[];
    equity_curve: EquityPoint[];
}

export interface BacktestParams {
    strategyName: string;
    ticker: string;
    source: 'Yahoo' | 'Topstep';
    contractId: string | null;
    interval: string;
    days: number;
    initialEquity: number;
    riskPerTrade: number;
    params: Record<string, number | string | boolean>;
}

export const api = {
    /**
     * Fetch available strategies from the backend
     */
    getStrategies: async (): Promise<Strategy[]> => {
        const res = await apiClient.get<Strategy[]>('/strategies');
        return res.data;
    },

    /**
     * Fetch available Topstep contracts
     */
    getTopstepContracts: async (): Promise<Contract[]> => {
        const res = await apiClient.get<Contract[]>('/topstep/contracts');
        return res.data;
    },

    /**
     * Run a backtest with the given parameters
     */
    runBacktest: async (
        strategyName: string,
        ticker: string,
        source: string,
        contractId: string | null,
        interval: string,
        days: number,
        initialEquity: number,
        riskPerTrade: number,
        params: Record<string, number | string | boolean>
    ): Promise<BacktestResult> => {
        const res = await apiClient.post<BacktestResult>('/backtest', {
            strategy_name: strategyName,
            ticker,
            source,
            contract_id: contractId,
            interval,
            days,
            initial_equity: initialEquity,
            risk_per_trade: riskPerTrade,
            params,
        });
        return res.data;
    },

    /**
     * Health check endpoint
     */
    healthCheck: async (): Promise<{ status: string; version: string }> => {
        const res = await apiClient.get<{ status: string; version: string }>('/health');
        return res.data;
    },
};
