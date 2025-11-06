export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

type DataSource = 'live' | 'fallback';

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

export interface ApiResponse<T> {
  data: T;
  source: DataSource;
  error?: string;
}

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = 5000;
const MAX_RETRIES = 3;
const RETRY_BASE_DELAY_MS = 250;

class HttpError extends Error {
  public status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'HttpError';
    this.status = status;
  }
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

async function requestOnce<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const controller = new AbortController();
  const timeout = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const url = `${API_BASE}${path}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers ?? {})
      },
      signal: controller.signal,
      ...options
    });

    if (!response.ok) {
      const message = await response.text();
      throw new HttpError(message || `Request failed with status ${response.status}`.trim(), response.status);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('Request timed out');
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

const isRetryableError = (error: unknown): boolean => {
  if (error instanceof HttpError) {
    return error.status >= 500;
  }
  if (error instanceof Error) {
    return error.message === 'Failed to fetch' || error.message === 'Request timed out';
  }
  return false;
};

async function requestWithRetry<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let attempt = 0;
  let lastError: unknown;

  while (attempt < MAX_RETRIES) {
    try {
      return await requestOnce<T>(path, options);
    } catch (error) {
      lastError = error;
      attempt += 1;
      if (attempt >= MAX_RETRIES || !isRetryableError(error)) {
        break;
      }
      const backoff = RETRY_BASE_DELAY_MS * 2 ** (attempt - 1);
      await sleep(backoff);
    }
  }

  throw lastError instanceof Error ? lastError : new Error('Unknown request error');
}

const FALLBACK_STRATEGIES: StrategySummary[] = [
  {
    id: 'momentum-pulse-v5',
    name: 'Momentum Pulse v5',
    description: 'High-frequency momentum aggregator fed by fused macro + flow signals.',
    category: 'Momentum'
  },
  {
    id: 'carry-radar-v2',
    name: 'Carry Radar v2',
    description: 'Rate differential aware carry rotation with macro risk filters.',
    category: 'Carry'
  },
  {
    id: 'liquidity-revert-v3',
    name: 'Liquidity Revert v3',
    description: 'Mean-reversion setup targeting liquidity sweeps with volatility throttles.',
    category: 'Mean Reversion'
  }
];

const seededRandom = (seed: string) => {
  let state = 0;
  for (let i = 0; i < seed.length; i += 1) {
    state = (state * 31 + seed.charCodeAt(i)) & 0xffffffff;
  }
  return () => {
    state = (1103515245 * state + 12345) & 0x7fffffff;
    return state / 0x80000000;
  };
};

const buildFallbackBacktest = (payload: BacktestRunPayload): BacktestRunResponse => {
  const { strategyId, symbol, bars = 120 } = payload;
  const random = seededRandom(`${strategyId}-${symbol}-${bars}`);
  const now = Date.now();
  const baseEquity = 100_000;
  const equityCurve: EquityPointResponse[] = Array.from({ length: bars }, (_, index) => {
    const progress = index / Math.max(bars - 1, 1);
    const drift = progress * 4_200;
    const noise = (random() - 0.5) * 500;
    return {
      timestamp: now - (bars - index) * 60_000,
      equity: Number((baseEquity + drift + noise).toFixed(2))
    };
  });

  const peak = equityCurve.reduce((max, point) => Math.max(max, point.equity), equityCurve[0]?.equity ?? baseEquity);
  const drawdownCurve: DrawdownPointResponse[] = equityCurve.map((point) => {
    const ratio = (peak - point.equity) / baseEquity;
    return {
      timestamp: point.timestamp,
      drawdown: Number((Math.max(0, ratio) * -100).toFixed(2))
    };
  });

  const trades: TradeRecordResponse[] = Array.from({ length: Math.min(40, Math.max(12, bars / 4)) }, (_, index) => {
    const direction = index % 2 === 0 ? 'LONG' : 'SHORT';
    const profit = Number(((random() - 0.45) * 350).toFixed(2));
    return {
      id: `${strategyId}-fallback-trade-${index}`,
      entryTime: now - (index + 2) * 45 * 60_000,
      exitTime: now - (index + 1) * 45 * 60_000,
      direction,
      profit,
      symbol
    };
  });

  const wins = trades.filter((trade) => trade.profit > 0).length;
  const netProfit = trades.reduce((total, trade) => total + trade.profit, 0);

  return {
    id: `${strategyId}-fallback-${now}`,
    strategy: strategyId,
    symbol,
    generatedAt: new Date(now).toISOString(),
    metrics: {
      netProfit: Number(netProfit.toFixed(2)),
      maxDrawdown: Number(Math.min(...drawdownCurve.map((point) => point.drawdown)).toFixed(2)),
      sharpeRatio: Number((1.4 + random() * 0.6).toFixed(2)),
      winRate: trades.length === 0 ? 0 : Number((wins / trades.length).toFixed(2)),
      trades: trades.length
    },
    equityCurve,
    drawdownCurve,
    trades
  };
};

const FALLBACK_DECISIONS: DecisionRecordResponse[] = [
  {
    id: 'dec-001',
    timestamp: Date.now() - 60_000,
    action: 'BUY',
    symbol: 'EURUSD',
    confidence: 0.72,
    summary: 'Momentum alignment across price and sentiment streams.',
    rationale: 'Price action forms higher high with positive sentiment delta and no conflicting macro events.',
    agentInsights: [
      { agent: 'Market Intelligence', statement: 'News sentiment shifted +0.32 in the last 3 minutes.' },
      { agent: 'Low-Level Reflection', statement: 'Latency within 75ms; price momentum intact.' },
      { agent: 'High-Level Reflection', statement: 'No conflicting positions; risk-on regime persists.' },
      { agent: 'Decision Agent', statement: 'Enter with 1.5% risk, stop below liquidity pocket at 1.0832.' }
    ],
    riskScore: 0.38
  },
  {
    id: 'dec-002',
    timestamp: Date.now() - 300_000,
    action: 'HOLD',
    symbol: 'GBPUSD',
    confidence: 0.54,
    summary: 'Conflicting macro sentiment – waiting for clarification.',
    rationale: 'Economic surprise index in UK remains negative; prefer to observe upcoming GDP release.',
    agentInsights: [
      { agent: 'Market Intelligence', statement: 'Social sentiment is neutral, article velocity decreasing.' },
      { agent: 'Low-Level Reflection', statement: 'Price volatility expanding, but no break in structure yet.' },
      { agent: 'High-Level Reflection', statement: 'Macro regime uncertain; risk budget nearly exhausted.' },
      { agent: 'Decision Agent', statement: 'Maintain current exposure; revisit after GDP print.' }
    ],
    riskScore: 0.61
  }
];

async function withFallback<T>(
  path: string,
  fallbackFactory: () => T | Promise<T>,
  options: RequestOptions = {}
): Promise<ApiResponse<T>> {
  try {
    const data = await requestWithRetry<T>(path, options);
    return { data, source: 'live' };
  } catch (error) {
    console.warn(`Falling back to mock payload for ${path}:`, error);
    const fallbackData = await fallbackFactory();
    const message = error instanceof Error ? error.message : 'Unknown error';
    return { data: fallbackData, source: 'fallback', error: message };
  }
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
  listStrategies: () =>
    withFallback<StrategySummary[]>(
      '/api/strategies',
      () => FALLBACK_STRATEGIES
    ),
  runBacktest: (payload: BacktestRunPayload) =>
    withFallback<BacktestRunResponse>(
      '/api/backtests/run',
      () => buildFallbackBacktest(payload),
      {
        method: 'POST',
        body: JSON.stringify(payload)
      }
    ),
  listDecisions: () => withFallback<DecisionRecordResponse[]>('/api/decisions', () => FALLBACK_DECISIONS)
};

export const socketUrl = (import.meta.env.VITE_SOCKET_URL as string | undefined) ?? API_BASE;

export type { ApiResponse, DataSource };
