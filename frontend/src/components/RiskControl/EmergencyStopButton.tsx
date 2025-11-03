import { useState } from 'react';

export default function EmergencyStopButton() {
  const [armed, setArmed] = useState(false);
  const [status, setStatus] = useState<'idle' | 'executed'>('idle');

  const toggleArm = () => {
    setArmed((prev) => !prev);
    setStatus('idle');
  };

  const triggerStop = () => {
    if (!armed) return;
    setStatus('executed');
    // In real integration, call backend endpoint to flatten positions immediately
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-white">Emergency Stop</h3>
        <p className="text-xs uppercase tracking-wide text-slate-500">Instant kill-switch for live trading</p>
      </div>
      <div className="rounded-xl border border-slate-800/70 bg-slate-900/80 p-4 text-sm text-slate-200">
        <p>
          When armed, this button triggers an immediate order flatten across all symbols and disables new order flow for five
          minutes.
        </p>
        <div className="mt-4 flex items-center gap-3">
          <button
            type="button"
            onClick={toggleArm}
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
              armed ? 'bg-slate-800 text-white' : 'bg-slate-700 text-slate-200 hover:bg-slate-600'
            }`}
          >
            {armed ? 'Disarm' : 'Arm Stop'}
          </button>
          <button
            type="button"
            onClick={triggerStop}
            disabled={!armed}
            className="rounded-lg bg-danger px-4 py-2 text-sm font-semibold text-white shadow shadow-danger/50 transition disabled:cursor-not-allowed disabled:bg-danger/40"
          >
            Trigger Stop
          </button>
        </div>
        <p className="mt-3 text-xs text-slate-400">
          Status:{' '}
          <span className={`font-semibold ${status === 'executed' ? 'text-danger' : 'text-slate-200'}`}>
            {status === 'executed' ? 'Stop triggered – trading halted' : armed ? 'Armed and ready' : 'Standby'}
          </span>
        </p>
      </div>
    </div>
  );
}
