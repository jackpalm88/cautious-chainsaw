import { useMemo } from 'react';
import { useBacktest } from '../../hooks/useBacktest';

export default function StrategySelector() {
  const {
    strategies,
    strategiesStatus,
    strategiesError,
    selectedStrategy,
    selectStrategy,
    run,
    runStatus
  } = useBacktest();

  const disabled = strategiesStatus !== 'success' || !selectedStrategy;
  const buttonLabel = runStatus === 'loading' ? 'Running…' : 'Run Backtest';

  const strategyOptions = useMemo(() => {
    if (strategiesStatus === 'loading') {
      return [<option key="loading">Loading strategies…</option>];
    }
    if (strategiesStatus === 'error') {
      return [
        <option key="error" value="">
          Failed to load strategies
        </option>
      ];
    }
    return strategies.map((strategy) => (
      <option key={strategy.id} value={strategy.id}>
        {strategy.name}
      </option>
    ));
  }, [strategies, strategiesStatus]);

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/70 px-4 py-2 sm:flex-row sm:items-center sm:gap-3">
      <label htmlFor="strategy" className="text-xs font-semibold uppercase tracking-wide text-slate-400">
        Strategy
      </label>
      <div className="flex w-full flex-1 items-center gap-3">
        <select
          id="strategy"
          value={selectedStrategy ?? ''}
          onChange={(event) => selectStrategy(event.target.value)}
          className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-slate-500 focus:outline-none"
          disabled={strategiesStatus !== 'success'}
        >
          {strategyOptions}
        </select>
        <button
          type="button"
          onClick={run}
          disabled={disabled || runStatus === 'loading'}
          className="rounded-lg bg-success/80 px-4 py-2 text-sm font-semibold text-slate-950 transition-colors hover:bg-success disabled:cursor-not-allowed disabled:bg-success/40"
        >
          {buttonLabel}
        </button>
      </div>
      {strategiesStatus === 'error' && strategiesError && (
        <p className="text-xs text-danger">{strategiesError}</p>
      )}
    </div>
  );
}
