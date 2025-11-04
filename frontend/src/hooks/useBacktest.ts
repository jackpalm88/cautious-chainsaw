import { useCallback } from 'react';
import { useBacktestStore } from '../stores/backtestStore';

export const useBacktest = () => {
  const { result, runBacktest, isLoading, selectedStrategy, selectStrategy, strategies } = useBacktestStore();

  const triggerRun = useCallback(() => {
    runBacktest().catch((error) => {
      console.error('Failed to run backtest', error);
    });
  }, [runBacktest]);

  return {
    result,
    isLoading,
    selectedStrategy,
    selectStrategy,
    strategies,
    run: triggerRun
  };
};
