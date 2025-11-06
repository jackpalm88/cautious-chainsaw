import { create } from 'zustand';
import { api, BacktestRunResponse, StrategySummary } from '../lib/api';

type AsyncStatus = 'idle' | 'loading' | 'success' | 'error';

export type BacktestResult = BacktestRunResponse;

interface BacktestStore {
  strategies: StrategySummary[];
  strategiesStatus: AsyncStatus;
  strategiesError: string | null;
  selectedStrategy: string | null;
  result: BacktestResult | null;
  runStatus: AsyncStatus;
  runError: string | null;
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
  selectedStrategy: null,
  result: null,
  runStatus: 'idle',
  runError: null,
  loadStrategies: async () => {
    if (get().strategiesStatus === 'loading') return;
    set({ strategiesStatus: 'loading', strategiesError: null });
    try {
      const strategies = await api.listStrategies();
      set({
        strategies,
        strategiesStatus: 'success',
        selectedStrategy: get().selectedStrategy ?? strategies[0]?.id ?? null
      });
    } catch (error) {
      set({ strategiesStatus: 'error', strategiesError: withErrorMessage(error) });
    }
  },
  selectStrategy: (strategyId: string) => {
    set({ selectedStrategy: strategyId });
  },
  runBacktest: async () => {
    const { selectedStrategy, runStatus } = get();
    if (!selectedStrategy || runStatus === 'loading') return;

    set({ runStatus: 'loading', runError: null });
    try {
      const response = await api.runBacktest({ strategyId: selectedStrategy, symbol: 'EURUSD' });
      set({ result: response, runStatus: 'success' });
    } catch (error) {
      set({ runStatus: 'error', runError: withErrorMessage(error) });
    }
  }
}));
