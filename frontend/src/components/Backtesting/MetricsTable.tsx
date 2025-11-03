import { useBacktestStore } from '../../stores/backtestStore';

const formatNumber = (value: number, suffix = '') => `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}${suffix}`;

export default function MetricsTable() {
  const { result } = useBacktestStore();

  const metrics = result?.metrics;

  return (
    <div>
      <h3 className="text-lg font-semibold text-white">Performance Metrics</h3>
      <p className="text-xs uppercase tracking-wide text-slate-500">Understand edge & risk in seconds</p>

      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <MetricCard label="Net Profit" value={metrics ? `$${formatNumber(metrics.netProfit)}` : '—'} />
        <MetricCard label="Max Drawdown" value={metrics ? `${metrics.maxDrawdown.toFixed(2)}%` : '—'} negative />
        <MetricCard label="Sharpe Ratio" value={metrics ? metrics.sharpeRatio.toFixed(2) : '—'} />
        <MetricCard label="Win Rate" value={metrics ? `${(metrics.winRate * 100).toFixed(1)}%` : '—'} />
        <MetricCard label="Trades" value={metrics ? formatNumber(metrics.trades) : '—'} />
      </div>
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: string;
  negative?: boolean;
}

function MetricCard({ label, value, negative }: MetricCardProps) {
  return (
    <div className="rounded-xl border border-slate-800/70 bg-slate-900/80 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-xl font-semibold ${negative ? 'text-danger' : 'text-white'}`}>{value}</p>
    </div>
  );
}
