import { create } from 'zustand';

export interface BacktestMetrics {
  netProfit: number;
  maxDrawdown: number;
  sharpeRatio: number;
  winRate: number;
  trades: number;
}

export interface TradeRecord {
  id: string;
  entryTime: number;
  exitTime: number;
  direction: 'LONG' | 'SHORT';
  profit: number;
  symbol: string;
}

export interface BacktestResult {
  id: string;
  equityCurve: { timestamp: number; equity: number }[];
  drawdownCurve: { timestamp: number; drawdown: number }[];
  metrics: BacktestMetrics;
  trades: TradeRecord[];
}

interface BacktestStore {
  strategies: string[];
  selectedStrategy: string;
  result: BacktestResult | null;
  isLoading: boolean;
  selectStrategy: (strategy: string) => void;
  runBacktest: () => Promise<void>;
}

const mockEquity = () =>
  Array.from({ length: 100 }, (_, idx) => ({
    timestamp: Date.now() - (100 - idx) * 60_000,
    equity: 100_000 + Math.sin(idx / 5) * 800 + idx * 120
  }));

const mockDrawdown = () =>
  Array.from({ length: 100 }, (_, idx) => ({
    timestamp: Date.now() - (100 - idx) * 60_000,
    drawdown: Math.abs(Math.sin(idx / 8) * 4)
  }));

const mockTrades = (): TradeRecord[] =>
  Array.from({ length: 25 }, (_, idx) => ({
    id: `trade-${idx}`,
    entryTime: Date.now() - (idx + 1) * 60 * 60 * 1000,
    exitTime: Date.now() - idx * 60 * 60 * 1000,
    direction: idx % 2 === 0 ? 'LONG' : 'SHORT',
    profit: Number((Math.random() * 200 - 50).toFixed(2)),
    symbol: 'EURUSD'
  }));

export const useBacktestStore = create<BacktestStore>((set, get) => ({
  strategies: ['Momentum Pulse v5', 'Carry Radar v2', 'Mean Reversion v3'],
  selectedStrategy: 'Momentum Pulse v5',
  result: null,
  isLoading: false,
  selectStrategy: (strategy: string) => set({ selectedStrategy: strategy }),
  runBacktest: async () => {
    if (get().isLoading) return;
    set({ isLoading: true });

    await new Promise((resolve) => setTimeout(resolve, 800));

    set({
      result: {
        id: `${get().selectedStrategy}-${Date.now()}`,
        equityCurve: mockEquity(),
        drawdownCurve: mockDrawdown(),
        metrics: {
          netProfit: 12840,
          maxDrawdown: -4.8,
          sharpeRatio: 1.92,
          winRate: 0.63,
          trades: 245
        },
        trades: mockTrades()
      },
      isLoading: false
    });
  }
}));
