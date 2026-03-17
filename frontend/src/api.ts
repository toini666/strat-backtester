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

export interface AvailableDataset {
    symbol: string;
    contract_id: string;
    timeframes: string[];
    start_date: string;
    end_date: string;
    bar_count_1m: number;
    min_start_per_strategy: Record<string, Record<string, string>>;
}

export interface TradeLeg {
    entry_time: string;
    entry_execution_time?: string | null;
    exit_time: string;
    exit_execution_time?: string | null;
    side: string;
    entry_price: number;
    exit_price: number;
    pnl: number;
    gross_pnl: number;
    fees: number;
    size: number;
    status: string;
}

export interface Trade {
    entry_time: string;
    entry_execution_time?: string | null;
    exit_time: string;
    exit_execution_time?: string | null;
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
    legs: TradeLeg[];
    excluded?: boolean;
}

export interface BlackoutWindowSettings {
    active: boolean;
    start_hour: number;
    start_minute: number;
    end_hour: number;
    end_minute: number;
}

export interface BacktestEngineSettings {
    auto_close_enabled: boolean;
    auto_close_hour: number;
    auto_close_minute: number;
    blackout_windows: BlackoutWindowSettings[];
    debug: boolean;
    daily_win_limit_enabled: boolean;
    daily_win_limit: number;
    daily_loss_limit_enabled: boolean;
    daily_loss_limit: number;
}

export const DEFAULT_BACKTEST_ENGINE_SETTINGS: BacktestEngineSettings = {
    auto_close_enabled: true,
    auto_close_hour: 22,
    auto_close_minute: 0,
    blackout_windows: [
        { active: false, start_hour: 0, start_minute: 0, end_hour: 0, end_minute: 5 },
        { active: false, start_hour: 9, start_minute: 0, end_hour: 9, end_minute: 5 },
        { active: true, start_hour: 12, start_minute: 0, end_hour: 14, end_minute: 0 },
        { active: false, start_hour: 15, start_minute: 30, end_hour: 15, end_minute: 35 },
        { active: true, start_hour: 16, start_minute: 30, end_hour: 22, end_minute: 0 },
        { active: true, start_hour: 22, start_minute: 0, end_hour: 23, end_minute: 59 },
    ],
    debug: false,
    daily_win_limit_enabled: false,
    daily_win_limit: 500,
    daily_loss_limit_enabled: false,
    daily_loss_limit: 700,
};

// --- Backtest Presets (Favorites) ---

export interface BacktestPreset {
    id: string;
    name: string;
    createdAt: string;
    // Data
    symbol: string;
    interval: string;
    startDatetime: string;
    endDatetime: string;
    // Risk
    initialEquity: number;
    riskPerTrade: number;
    maxContracts: number;
    // Strategy
    strategyName: string;
    params: Record<string, number | string | boolean>;
    // Engine
    engineSettings: BacktestEngineSettings;
}

const PRESETS_STORAGE_KEY = 'nebular_backtest_presets';

export function loadPresets(): BacktestPreset[] {
    try {
        const raw = localStorage.getItem(PRESETS_STORAGE_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

export function savePreset(preset: BacktestPreset): BacktestPreset[] {
    const presets = loadPresets();
    presets.unshift(preset);
    localStorage.setItem(PRESETS_STORAGE_KEY, JSON.stringify(presets));
    return presets;
}

export function deletePreset(id: string): BacktestPreset[] {
    const presets = loadPresets().filter((p) => p.id !== id);
    localStorage.setItem(PRESETS_STORAGE_KEY, JSON.stringify(presets));
    return presets;
}

export function renamePreset(id: string, name: string): BacktestPreset[] {
    const presets = loadPresets().map((p) => (p.id === id ? { ...p, name } : p));
    localStorage.setItem(PRESETS_STORAGE_KEY, JSON.stringify(presets));
    return presets;
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
    daily_limits_hit?: Record<string, string>;  // date -> "win"|"loss"
    data_source_used?: string | null;
    debug_file?: string | null;
}

// Market Data Store
export interface RolloverInfo {
    from_contract: string;
    to_contract: string;
    date: string;
    next_contract_id: string;
}

export interface ContractSegment {
    contract: string;
    label: string;
    from: string;
    to: string;
}

export interface MarketDataset {
    id: string;
    symbol: string;
    contract_id: string;
    start_date: string;
    end_date: string;
    bar_count_1m: number;
    total_size_mb: number;
    timeframes: string[];
    timezone: string;
    updated_at: string;
    missing_hours: number;
    missing_days: number;
    days_until_retention_limit: number;
    retention_warning: boolean;
    retention_exceeded: boolean;
    next_rollover: RolloverInfo | null;
    contract_segments: ContractSegment[];
}

export interface DownloadStatus {
    download_id: string;
    status: 'in_progress' | 'completed' | 'failed';
    progress: number;
    bars_downloaded: number;
    message: string;
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
     * Fetch available local data (symbols, timeframes, date ranges)
     */
    getAvailableData: async (): Promise<AvailableDataset[]> => {
        const res = await apiClient.get<AvailableDataset[]>('/available-data');
        return res.data;
    },

    /**
     * Run a backtest with the given parameters
     */
    runBacktest: async (
        strategyName: string,
        symbol: string,
        interval: string,
        startDatetime: string,
        endDatetime: string,
        initialEquity: number,
        riskPerTrade: number,
        params: Record<string, number | string | boolean>,
        maxContracts: number = 50,
        engineSettings: BacktestEngineSettings = DEFAULT_BACKTEST_ENGINE_SETTINGS,
    ): Promise<BacktestResult> => {
        const res = await apiClient.post<BacktestResult>('/backtest', {
            strategy_name: strategyName,
            symbol,
            interval,
            start_datetime: startDatetime,
            end_datetime: endDatetime,
            initial_equity: initialEquity,
            risk_per_trade: riskPerTrade,
            params,
            max_contracts: maxContracts,
            engine_settings: engineSettings,
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
            topstep_live_mode: request.topstepLiveMode,
            max_drawdown_limit: request.maxDrawdownLimit,
            min_win_rate: request.minWinRate
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

    // --- Market Data Store ---

    /**
     * List all locally stored datasets
     */
    getMarketData: async (): Promise<MarketDataset[]> => {
        const res = await apiClient.get<MarketDataset[]>('/market-data');
        return res.data;
    },

    /**
     * Start downloading 1-minute bars for a contract
     */
    downloadMarketData: async (contractId: string, startDate: string, endDate: string): Promise<{ download_id: string }> => {
        const res = await apiClient.post<{ download_id: string }>('/market-data/download', {
            contract_id: contractId,
            start_date: startDate,
            end_date: endDate,
        });
        return res.data;
    },

    /**
     * Poll download progress
     */
    getDownloadStatus: async (downloadId: string): Promise<DownloadStatus> => {
        const res = await apiClient.get<DownloadStatus>(`/market-data/download/${downloadId}/status`);
        return res.data;
    },

    /**
     * Delete a local dataset
     */
    deleteMarketData: async (datasetId: string): Promise<void> => {
        await apiClient.delete(`/market-data/${datasetId}`);
    },
};

// Optimization types
export interface ParamRangeInfo {
    name: string;
    values: (number | boolean | string)[];
    default: number | boolean | string;
    param_type: 'float' | 'int' | 'bool' | 'str_options';
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
    param_type: 'float' | 'int' | 'bool' | 'str_options';
    str_values?: string[];  // For str_options type
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
    maxDrawdownLimit?: number;
    minWinRate?: number;
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
    parameters?: ParameterRangeInput[];
    total_combinations: number;
    top_results: OptimizationResultItem[];
    max_drawdown_limit?: number;
    min_win_rate?: number;
}
