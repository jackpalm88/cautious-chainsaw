import { useMemo } from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, Line } from 'recharts';
import { useFusionStore } from '../../stores/fusionStore';

const formatTime = (timestamp: number) => new Date(timestamp).toLocaleTimeString();

export default function SentimentPanel() {
  const { sentimentBuffer } = useFusionStore((state) => ({ sentimentBuffer: state.sentimentBuffer }));

  const data = useMemo(
    () =>
      sentimentBuffer.map((point) => ({
        time: formatTime(point.timestamp),
        score: Number(point.score.toFixed(2)),
        headline: point.latestHeadline
      })),
    [sentimentBuffer]
  );

  const latest = data.at(-1);
  const statusColor = latest
    ? latest.score > 0.2
      ? 'text-success'
      : latest.score < -0.2
      ? 'text-danger'
      : 'text-warning'
    : 'text-slate-400';

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">Sentiment Stream</h3>
          <p className="text-xs uppercase tracking-wide text-slate-500">News velocity & confidence</p>
        </div>
        <div className={`text-right text-2xl font-semibold ${statusColor}`}>
          {latest ? latest.score.toFixed(2) : '—'}
          <div className="text-xs text-slate-500">Normalized score</div>
        </div>
      </header>

      <div className="mt-4 h-48">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data.slice(-120)}>
            <defs>
              <linearGradient id="sentimentGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="time" tick={{ fill: '#94a3b8', fontSize: 11 }} minTickGap={30} />
            <YAxis domain={[-1, 1]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12 }}
              labelStyle={{ color: '#cbd5f5' }}
            />
            <Area type="monotone" dataKey="score" stroke="#38bdf8" fill="url(#sentimentGradient)" strokeWidth={2} />
            <Line type="monotone" dataKey="score" stroke="#f472b6" strokeWidth={1.5} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 space-y-2 text-sm text-slate-300">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Latest Headlines</h4>
        {data.slice(-5).reverse().map((item, index) => (
          <p key={`${item.time}-${index}`} className="rounded-lg border border-slate-800/70 bg-slate-900/80 p-2">
            <span className="mr-2 text-xs text-slate-500">{item.time}</span>
            {item.headline}
          </p>
        ))}
        {data.length === 0 && <p className="text-xs text-slate-500">Waiting for sentiment feed…</p>}
      </div>
    </div>
  );
}
