import axios from 'axios';

const API_URL = 'http://localhost:8001';

export interface Strategy {
    name: string;
    description: string;
    default_params: Record<string, any>;
}

export interface Contract {
    id: string;
    name: string;
    description: string;
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

export interface BacktestResult {
    metrics: {
        total_return: number;
        win_rate: number;
        total_trades: number;
        max_drawdown: number;
        sharpe_ratio: number;
    };
    trades: Trade[];
    equity_curve: { time: string; value: number }[];
}

export const api = {
    getStrategies: async (): Promise<Strategy[]> => {
        const res = await axios.get(`${API_URL}/strategies`);
        return res.data;
    },

    getTopstepContracts: async (): Promise<Contract[]> => {
        const res = await axios.get(`${API_URL}/topstep/contracts`);
        return res.data;
    },

    runBacktest: async (
        strategyName: string,
        ticker: string,
        source: string,
        contractId: string | null,
        interval: string,
        days: number,
        initialEquity: number,
        riskPerTrade: number,
        params: Record<string, any>
    ): Promise<BacktestResult> => {
        const res = await axios.post(`${API_URL}/backtest`, {
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
};
