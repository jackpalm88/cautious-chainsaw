import { SyncStatus } from '../../stores/fusionStore';

const STATUS_COPY: Record<SyncStatus, { label: string; color: string; description: string }> = {
  disconnected: {
    label: 'Disconnected',
    color: 'bg-slate-500',
    description: 'Attempting to reconnect…'
  },
  synced: {
    label: 'Synced',
    color: 'bg-emerald-500',
    description: 'All streams within 100ms window.'
  },
  delayed: {
    label: 'Delayed',
    color: 'bg-amber-400',
    description: 'Detected 100-500ms delay. Monitor closely.'
  },
  stale: {
    label: 'Stale',
    color: 'bg-rose-500',
    description: 'Data >500ms behind. Avoid execution.'
  }
};

interface Props {
  status: SyncStatus;
  latencyMs?: number | null;
  mode?: 'live' | 'mock';
}

export default function SyncIndicator({ status, latencyMs, mode = 'live' }: Props) {
  const copy = STATUS_COPY[status];
  return (
    <div className="flex items-center gap-3 rounded-full border border-slate-800 bg-slate-900/80 px-4 py-2 shadow shadow-slate-950/40">
      <span className={`h-2.5 w-2.5 rounded-full ${copy.color}`} />
      <div>
        <div className="text-sm font-semibold text-white">{copy.label}</div>
        <p className="text-xs text-slate-400">{copy.description}</p>
        <p className="text-xs text-slate-500">
          {latencyMs != null ? `Latency: ${Math.round(latencyMs)}ms` : 'Latency unavailable'} ·
          <span className="ml-1 capitalize">{mode === 'mock' ? 'Preview stream' : 'Live stream'}</span>
        </p>
      </div>
    </div>
  );
}
