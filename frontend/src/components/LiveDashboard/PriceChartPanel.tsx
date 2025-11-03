import { useMemo } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Line
} from 'recharts';
import { useFusionStore } from '../../stores/fusionStore';

interface PricePoint {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

const formatTime = (timestamp: number) => new Date(timestamp).toLocaleTimeString();

export default function PriceChartPanel() {
  const { priceBuffer, latencyMs } = useFusionStore((state) => ({
    priceBuffer: state.priceBuffer,
    latencyMs: state.latencyMs
  }));

  const chartData = useMemo<PricePoint[]>(
    () =>
      priceBuffer.map((point) => ({
        time: formatTime(point.timestamp),
        open: Number(point.open.toFixed(5)),
        high: Number(point.high.toFixed(5)),
        low: Number(point.low.toFixed(5)),
        close: Number(point.close.toFixed(5)),
        volume: point.volume
      })),
    [priceBuffer]
  );

  const latest = chartData.at(-1);
  const previous = chartData.at(-2);
  const delta = latest && previous ? latest.close - previous.close : 0;
  const deltaPct = latest && previous ? (delta / previous.close) * 100 : 0;

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">Price & Volume</h3>
          <p className="text-xs uppercase tracking-wide text-slate-500">100ms fused data stream</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-semibold text-white">
            {latest ? latest.close.toFixed(5) : '—'}
            <span className={`ml-2 text-sm ${delta >= 0 ? 'text-success' : 'text-danger'}`}>
              {delta >= 0 ? '+' : ''}{delta.toFixed(5)} ({deltaPct.toFixed(2)}%)
            </span>
          </div>
          <div className="text-xs text-slate-500">Latency: {latencyMs ? `${latencyMs.toFixed(0)}ms` : '—'}</div>
        </div>
      </header>

      <div className="mt-4 flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData.slice(-120)} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="rgba(148, 163, 184, 0.15)" strokeDasharray="3 3" />
            <XAxis dataKey="time" tick={{ fill: '#94a3b8', fontSize: 11 }} minTickGap={30} />
            <YAxis
              yAxisId="price"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              domain={['dataMin - 0.0015', 'dataMax + 0.0015']}
            />
            <YAxis yAxisId="volume" orientation="right" tick={{ fill: '#64748b', fontSize: 10 }} hide />
            <Tooltip
              contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12 }}
              labelStyle={{ color: '#cbd5f5' }}
            />
            <Bar yAxisId="volume" dataKey="volume" fill="#1d4ed8" opacity={0.35} />
            <Line
              yAxisId="price"
              type="monotone"
              dataKey="close"
              stroke="#38bdf8"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
