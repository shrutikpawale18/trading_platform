export interface Bar {
    timestamp: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
}

export interface Order {
    order_id: string;
    client_order_id: string;
    status: string;
    symbol: string;
    qty: string;
    filled_qty: string;
    filled_avg_price: string | null;
}

export interface Position {
    symbol: string;
    quantity: number;
    entry_price: number;
    current_price: number;
    status: 'OPEN' | 'CLOSED';
    timestamp: string;
}

export interface Asset {
    id: string;
    symbol: string;
    name: string;
    status: string;
    tradable: boolean;
    marginable: boolean;
    shortable: boolean;
    easy_to_borrow: boolean;
    fractionable: boolean;
}

export interface AccountInfo {
    account_number: string;
    status: string;
    equity: string;
    buying_power: string;
    cash: string;
    currency: string;
    paper_trading: boolean;
}

export interface APIError {
    message: string;
    status: number;
    code?: string;
}

export type TimeFrame = '1Min' | '5Min' | '15Min' | '1H' | '1D';

export interface HistoricalBarsParams {
    symbol: string;
    timeframe?: TimeFrame;
    lookback_days?: number;
    start_date?: string;
    end_date?: string;
    limit?: number;
}

export interface OrderRequest {
    symbol: string;
    quantity: number;
    side: 'buy' | 'sell';
    time_in_force?: 'day' | 'gtc';
}

export interface PositionRequest {
    symbol: string;
}

export interface BarResponse {
    timestamp: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
}

export interface OrderResponse {
    order_id: string;
    client_order_id: string;
    status: string;
    symbol: string;
    qty: string;
    filled_qty: string;
    filled_avg_price: string | null;
}

export interface PositionResponse {
    symbol: string;
    quantity: number;
    entry_price: number;
    current_price: number;
    status: string;
    timestamp: string;
} 