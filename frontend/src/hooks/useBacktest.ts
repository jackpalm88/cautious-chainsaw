import { useCallback, useEffect } from 'react';
import { useBacktestStore } from '../stores/backtestStore';

export const useBacktest = () => {
  const {
    result,
    runBacktest,
    runStatus,
    runError,
    runNotice,
    resultSource,
    selectedStrategy,
    selectStrategy,
    strategies,
    strategiesStatus,
    strategiesError,
    strategiesNotice,
    strategiesSource,
    loadStrategies
  } = useBacktestStore();

  useEffect(() => {
    if (strategiesStatus === 'idle') {
      loadStrategies().catch((error) => {
        console.error('Failed to load strategies', error);
      });
    }
  }, [strategiesStatus, loadStrategies]);

  const triggerRun = useCallback(() => {
    runBacktest().catch((error) => {
      console.error('Failed to run backtest', error);
    });
  }, [runBacktest]);

  return {
    result,
    runStatus,
    runError,
    runNotice,
    resultSource,
    selectedStrategy,
    selectStrategy,
    strategies,
    strategiesStatus,
    strategiesError,
    strategiesNotice,
    strategiesSource,
    run: triggerRun
  };
};
