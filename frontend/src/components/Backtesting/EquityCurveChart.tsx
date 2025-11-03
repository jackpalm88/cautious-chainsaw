import { useMemo } from 'react';
import { ResponsiveContainer, ComposedChart, Area, XAxis, YAxis, Tooltip, Legend, Line } from 'recharts';
import { useBacktestStore } from '../../stores/backtestStore';

const formatTime = (timestamp: number) => new Date(timestamp).toLocaleTimeString();

export default function EquityCurveChart() {
  const { result } = useBacktestStore();

  const data = useMemo(() => {
    if (!result) return [];
    return result.equityCurve.map((point, index) => ({
      timestamp: point.timestamp,
      equity: point.equity,
      drawdown: result.drawdownCurve[index]?.drawdown ?? 0
    }));
  }, [result]);

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">Equity & Drawdown</h3>
          <p className="text-xs uppercase tracking-wide text-slate-500">Interactive backtest visualization</p>
        </div>
        <div className="text-xs text-slate-400">Sampled {data.length} points</div>
      </header>

      <div className="mt-4 h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.6} />
                <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="timestamp" tickFormatter={formatTime} tick={{ fill: '#94a3b8', fontSize: 11 }} minTickGap={30} />
            <YAxis yAxisId="equity" tick={{ fill: '#94a3b8', fontSize: 11 }} domain={['auto', 'auto']} />
            <YAxis yAxisId="drawdown" orientation="right" tick={{ fill: '#f97316', fontSize: 11 }} domain={[-10, 0]} />
            <Tooltip
              contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12 }}
              labelFormatter={(value) => formatTime(Number(value))}
            />
            <Legend verticalAlign="top" align="right" wrapperStyle={{ color: '#cbd5f5' }} />
            <Area
              yAxisId="equity"
              type="monotone"
              dataKey="equity"
              name="Equity"
              stroke="#22d3ee"
              fill="url(#equityGradient)"
            />
            <Line
              yAxisId="drawdown"
              type="monotone"
              dataKey="drawdown"
              name="Drawdown %"
              stroke="#f97316"
              strokeWidth={2}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
