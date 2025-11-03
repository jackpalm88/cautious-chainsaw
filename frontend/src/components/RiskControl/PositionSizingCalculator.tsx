import { useMemo, useState } from 'react';

export default function PositionSizingCalculator() {
  const [accountSize, setAccountSize] = useState(100_000);
  const [riskPercent, setRiskPercent] = useState(1.5);
  const [stopDistance, setStopDistance] = useState(45);

  const positionSize = useMemo(() => {
    const riskCapital = (accountSize * riskPercent) / 100;
    if (stopDistance <= 0) return 0;
    return Math.round((riskCapital / stopDistance) * 1_000) / 1_000;
  }, [accountSize, riskPercent, stopDistance]);

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-white">Position Sizing</h3>
        <p className="text-xs uppercase tracking-wide text-slate-500">Kelly-aware fractional risk controls</p>
      </div>

      <form className="space-y-3 text-sm text-slate-200">
        <label className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wide text-slate-500">Account Size ($)</span>
          <input
            type="number"
            min={1000}
            step={1000}
            value={accountSize}
            onChange={(event) => setAccountSize(Number(event.target.value))}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 focus:border-slate-500 focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wide text-slate-500">Risk per Trade (%)</span>
          <input
            type="number"
            min={0.1}
            step={0.1}
            value={riskPercent}
            onChange={(event) => setRiskPercent(Number(event.target.value))}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 focus:border-slate-500 focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wide text-slate-500">Stop Distance (pips)</span>
          <input
            type="number"
            min={1}
            step={1}
            value={stopDistance}
            onChange={(event) => setStopDistance(Number(event.target.value))}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 focus:border-slate-500 focus:outline-none"
          />
        </label>
      </form>

      <div className="rounded-xl border border-slate-800/70 bg-slate-900/80 p-4 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Recommended Size</span>
          <span className="text-xl font-semibold text-white">{positionSize.toLocaleString()} lots</span>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Based on Kelly criterion with risk offset. Adjust stop distance or risk budget to fine-tune sizing.
        </p>
      </div>
    </div>
  );
}
