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
    startDate?: string;
    endDate?: string;
    topstepLiveMode?: boolean;
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
        params: Record<string, number | string | boolean>,
        maxContracts: number = 50,
        blockMarketOpen: boolean = true,
        startDate?: string,
        endDate?: string,
        topstepLiveMode?: boolean
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
            max_contracts: maxContracts,
            block_market_open: blockMarketOpen,
            start_date: startDate,
            end_date: endDate,
            topstep_live_mode: topstepLiveMode
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

    /**
     * Get parameter ranges for a strategy
     */
    getStrategyParamRanges: async (strategyName: string): Promise<StrategyParamRanges> => {
        const res = await apiClient.get<StrategyParamRanges>(`/strategy-param-ranges/${strategyName}`);
        return res.data;
    },

    /**
     * Run parameter optimization
     */
    runOptimization: async (request: OptimizationRequest): Promise<OptimizationResponse> => {
        const res = await apiClient.post<OptimizationResponse>('/optimize', {
            strategy_name: request.strategyName,
            ticker: request.ticker,
            source: request.source,
            contract_id: request.contractId,
            interval: request.interval,
            days: request.days,
            parameters: request.parameters,
            sessions: request.sessions,
            initial_equity: request.initialEquity,
            risk_per_trade: request.riskPerTrade,
            max_workers: request.maxWorkers,
            max_contracts: request.maxContracts,
            block_market_open: request.blockMarketOpen,
            start_date: request.startDate,
            end_date: request.endDate,
            topstep_live_mode: request.topstepLiveMode
        }, {
            timeout: 600000, // 10 minutes for optimization
        });
        return res.data;
    },

    /**
     * Get optimization history
     */
    getOptimizationHistory: async (): Promise<OptimizationHistoryItem[]> => {
        const res = await apiClient.get<OptimizationHistoryItem[]>('/optimization-history');
        return res.data;
    },

    /**
     * Get a specific optimization run
     */
    getOptimizationRun: async (runId: string): Promise<OptimizationRunDetail> => {
        const res = await apiClient.get<OptimizationRunDetail>(`/optimization-history/${runId}`);
        return res.data;
    },
    /**
     * Delete an optimization run
     */
    deleteOptimizationRun: async (runId: string): Promise<void> => {
        await apiClient.delete(`/optimization-history/${runId}`);
    },
    /**
     * Toggle favorite status of an optimization run
     */
    toggleOptimizationFavorite: async (runId: string): Promise<boolean> => {
        const res = await apiClient.post<{ status: string; is_favorite: boolean }>(`/optimization-history/${runId}/favorite`);
        return res.data.is_favorite;
    },

    /**
     * Delete multiple optimization runs
     */
    bulkDeleteOptimizationRuns: async (runIds: string[]): Promise<void> => {
        await apiClient.post('/optimization-history/bulk-delete', { run_ids: runIds });
    },
};

// Optimization types
export interface ParamRangeInfo {
    name: string;
    values: (number | boolean)[];
    default: number | boolean;
    param_type: 'float' | 'int' | 'bool';
    count: number;
}

export interface StrategyParamRanges {
    strategy_name: string;
    param_ranges: ParamRangeInfo[];
    total_combinations: number;
}

export interface ParameterRangeInput {
    name: string;
    min_value: number;
    max_value: number;
    step: number;
    param_type: 'float' | 'int' | 'bool';
}

export interface OptimizationRequest {
    strategyName: string;
    ticker: string;
    source: 'Yahoo' | 'Topstep';
    contractId: string | null;
    interval: string;
    days: number;
    parameters: ParameterRangeInput[];
    sessions: string[];
    initialEquity: number;
    riskPerTrade: number;
    maxWorkers: number;
    maxContracts: number;
    blockMarketOpen: boolean;
    startDate?: string;
    endDate?: string;
    topstepLiveMode?: boolean;
}

export interface OptimizationResultItem {
    rank: number;
    parameters: Record<string, number | boolean>;
    sessions: string[];
    total_return: number;
    win_rate: number;
    trade_count: number;
    max_drawdown: number;
}

export interface OptimizationResponse {
    id: string;
    strategy_name: string;
    total_combinations: number;
    completed: number;
    top_results: OptimizationResultItem[];
    errors: number;
}

export interface OptimizationHistoryItem {
    id: string;
    timestamp: string;
    strategy_name: string;
    contract_id: string | null;
    ticker: string;
    source: string;
    interval: string;
    days: number;
    total_combinations: number;
    best_return: number;
    start_date?: string;
    end_date?: string;
    is_favorite: boolean;
}

export interface OptimizationRunDetail {
    id: string;
    timestamp: string;
    strategy_name: string;
    contract_id: string | null;
    ticker: string;
    source: string;
    interval: string;
    days: number;
    start_date?: string;
    end_date?: string;
    topstep_live_mode?: boolean;
    initial_equity?: number;
    risk_per_trade?: number;
    max_contracts?: number;
    block_market_open?: boolean;
    sessions_tested: string[];
    parameters?: ParameterRangeInput[]; // Optional for backward compatibility
    total_combinations: number;
    top_results: OptimizationResultItem[];
}
