export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8000';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {})
    },
    ...options
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export interface StrategySummary {
  id: string;
  name: string;
  description: string;
  category: string;
}

export interface BacktestRunPayload {
  strategyId: string;
  symbol: string;
  bars?: number;
}

export interface BacktestMetricsResponse {
  netProfit: number;
  maxDrawdown: number;
  sharpeRatio: number;
  winRate: number;
  trades: number;
}

export interface EquityPointResponse {
  timestamp: number;
  equity: number;
}

export interface DrawdownPointResponse {
  timestamp: number;
  drawdown: number;
}

export interface TradeRecordResponse {
  id: string;
  entryTime: number;
  exitTime: number;
  direction: 'LONG' | 'SHORT';
  profit: number;
  symbol: string;
}

export interface BacktestRunResponse {
  id: string;
  strategy: string;
  symbol: string;
  generatedAt: string;
  metrics: BacktestMetricsResponse;
  equityCurve: EquityPointResponse[];
  drawdownCurve: DrawdownPointResponse[];
  trades: TradeRecordResponse[];
}

export interface DecisionAgentInsightResponse {
  agent: string;
  statement: string;
}

export interface DecisionRecordResponse {
  id: string;
  timestamp: number;
  action: 'BUY' | 'SELL' | 'HOLD';
  symbol: string;
  confidence: number;
  summary: string;
  rationale: string;
  riskScore: number;
  agentInsights: DecisionAgentInsightResponse[];
}

export const api = {
  listStrategies: () => request<StrategySummary[]>('/api/strategies'),
  runBacktest: (payload: BacktestRunPayload) =>
    request<BacktestRunResponse>('/api/backtests/run', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  listDecisions: () => request<DecisionRecordResponse[]>('/api/decisions')
};

export const socketUrl = (import.meta.env.VITE_SOCKET_URL as string | undefined) ?? API_BASE;
