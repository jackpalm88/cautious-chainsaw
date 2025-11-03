import { useMemo } from 'react';
import { useFusionStore } from '../../stores/fusionStore';

const IMPACT_COLOR: Record<'low' | 'medium' | 'high', string> = {
  low: 'bg-success/80',
  medium: 'bg-warning/80',
  high: 'bg-danger/80'
};

const formatTime = (timestamp: number) => new Date(timestamp).toLocaleTimeString();

export default function EconomicEventsPanel() {
  const { eventBuffer } = useFusionStore((state) => ({ eventBuffer: state.eventBuffer }));
  const events = useMemo(() => [...eventBuffer].slice(-12).reverse(), [eventBuffer]);

  return (
    <div className="h-full">
      <header className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">Economic Event Timeline</h3>
          <p className="text-xs uppercase tracking-wide text-slate-500">Impact-aware global macro feed</p>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-success/80" /> Low
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-warning/80" /> Medium
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-danger/80" /> High
          </span>
        </div>
      </header>

      <div className="mt-4 space-y-3">
        {events.length === 0 && <p className="text-sm text-slate-500">Awaiting economic calendar stream…</p>}
        {events.map((event) => (
          <div key={event.id} className="flex items-start gap-4">
            <div className="flex flex-col items-center">
              <span className={`h-2 w-2 rounded-full ${IMPACT_COLOR[event.impact]}`} />
              <span className="mt-2 block h-full w-px bg-slate-800" />
            </div>
            <div className="flex-1 rounded-xl border border-slate-800/70 bg-slate-900/80 p-3">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-white">{event.name}</span>
                <span className="text-xs text-slate-500">{formatTime(event.timestamp)}</span>
              </div>
              <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-400">
                {event.actual && (
                  <span>
                    Actual: <span className="text-slate-200">{event.actual}</span>
                  </span>
                )}
                {event.forecast && (
                  <span>
                    Forecast: <span className="text-slate-200">{event.forecast}</span>
                  </span>
                )}
                <span>
                  Impact:
                  <span className="ml-1 capitalize text-slate-200">{event.impact}</span>
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
