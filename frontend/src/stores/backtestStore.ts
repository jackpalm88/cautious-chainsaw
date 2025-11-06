import { create } from 'zustand';
import { api, BacktestRunResponse, StrategySummary, DataSource } from '../lib/api';

type AsyncStatus = 'idle' | 'loading' | 'success' | 'error';

export type BacktestResult = BacktestRunResponse;

interface BacktestStore {
  strategies: StrategySummary[];
  strategiesStatus: AsyncStatus;
  strategiesError: string | null;
  strategiesSource: DataSource | null;
  strategiesNotice: string | null;
  selectedStrategy: string | null;
  result: BacktestResult | null;
  resultSource: DataSource | null;
  runStatus: AsyncStatus;
  runError: string | null;
  runNotice: string | null;
  loadStrategies: () => Promise<void>;
  selectStrategy: (strategyId: string) => void;
  runBacktest: () => Promise<void>;
}

const withErrorMessage = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }
  return 'Unexpected error occurred';
};

export const useBacktestStore = create<BacktestStore>((set, get) => ({
  strategies: [],
  strategiesStatus: 'idle',
  strategiesError: null,
  strategiesSource: null,
  strategiesNotice: null,
  selectedStrategy: null,
  result: null,
  resultSource: null,
  runStatus: 'idle',
  runError: null,
  runNotice: null,
  loadStrategies: async () => {
    if (get().strategiesStatus === 'loading') return;
    set({ strategiesStatus: 'loading', strategiesError: null });
    try {
      const response = await api.listStrategies();
      const { data: strategies, source, error } = response;
      set({
        strategies,
        strategiesStatus: 'success',
        strategiesSource: source,
        strategiesNotice:
          source === 'fallback'
            ? error ?? 'Using offline strategies while API reconnects.'
            : null,
        selectedStrategy: get().selectedStrategy ?? strategies[0]?.id ?? null
      });
    } catch (error) {
      set({
        strategiesStatus: 'error',
        strategiesError: withErrorMessage(error),
        strategiesNotice: null,
        strategiesSource: null
      });
    }
  },
  selectStrategy: (strategyId: string) => {
    set({ selectedStrategy: strategyId });
  },
  runBacktest: async () => {
    const { selectedStrategy, runStatus } = get();
    if (!selectedStrategy || runStatus === 'loading') return;

    set({ runStatus: 'loading', runError: null, runNotice: null });
    try {
      const { data, source, error } = await api.runBacktest({
        strategyId: selectedStrategy,
        symbol: 'EURUSD'
      });
      set({
        result: data,
        resultSource: source,
        runStatus: 'success',
        runNotice:
          source === 'fallback'
            ? error ?? 'Showing simulated backtest while API is unreachable.'
            : null
      });
    } catch (error) {
      set({ runStatus: 'error', runError: withErrorMessage(error), runNotice: null });
    }
  }
}));
