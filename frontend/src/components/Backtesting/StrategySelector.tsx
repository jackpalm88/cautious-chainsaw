import { useBacktest } from '../../hooks/useBacktest';

export default function StrategySelector() {
  const { strategies, selectedStrategy, selectStrategy, run, isLoading } = useBacktest();

  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/70 px-4 py-2">
      <label htmlFor="strategy" className="text-xs font-semibold uppercase tracking-wide text-slate-400">
        Strategy
      </label>
      <select
        id="strategy"
        value={selectedStrategy}
        onChange={(event) => selectStrategy(event.target.value)}
        className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-slate-500 focus:outline-none"
      >
        {strategies.map((strategy) => (
          <option key={strategy} value={strategy}>
            {strategy}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={run}
        disabled={isLoading}
        className="rounded-lg bg-success/80 px-4 py-2 text-sm font-semibold text-slate-950 transition-colors hover:bg-success disabled:cursor-not-allowed disabled:bg-success/40"
      >
        {isLoading ? 'Running…' : 'Run Backtest'}
      </button>
    </div>
  );
}
