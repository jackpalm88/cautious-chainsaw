import { SyncStatus } from '../../stores/fusionStore';

const STATUS_COPY: Record<SyncStatus, { label: string; color: string; description: string }> = {
  disconnected: {
    label: 'Disconnected',
    color: 'bg-slate-600',
    description: 'Attempting to reconnect…'
  },
  synced: {
    label: 'Synced',
    color: 'bg-success',
    description: 'All streams within 100ms window.'
  },
  delayed: {
    label: 'Delayed',
    color: 'bg-warning',
    description: 'Detected 100-500ms delay. Monitor closely.'
  },
  stale: {
    label: 'Stale',
    color: 'bg-danger',
    description: 'Data >500ms behind. Avoid execution.'
  }
};

interface Props {
  status: SyncStatus;
}

export default function SyncIndicator({ status }: Props) {
  const copy = STATUS_COPY[status];
  return (
    <div className="flex items-center gap-3 rounded-full border border-slate-800 bg-slate-900/80 px-4 py-2 shadow shadow-slate-950/40">
      <span className={`h-2.5 w-2.5 rounded-full ${copy.color}`} />
      <div>
        <div className="text-sm font-semibold text-white">{copy.label}</div>
        <p className="text-xs text-slate-400">{copy.description}</p>
      </div>
    </div>
  );
}
