import type { DecisionRecord } from '../../stores/decisionStore';

interface Props {
  decision: DecisionRecord | null;
}

export default function DecisionDetailModal({ decision }: Props) {
  if (!decision) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 p-6 text-center text-slate-500">
        <p className="text-sm">Select a decision from the log to inspect the full INoT debate.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">Decision Detail</h3>
          <p className="text-xs uppercase tracking-wide text-slate-500">{decision.symbol}</p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            decision.action === 'BUY'
              ? 'bg-success/30 text-success'
              : decision.action === 'SELL'
              ? 'bg-danger/30 text-danger'
              : 'bg-warning/30 text-warning'
          }`}
        >
          {decision.action}
        </span>
      </header>

      <div className="mt-4 space-y-4 text-sm text-slate-300">
        <section className="rounded-xl border border-slate-800/70 bg-slate-950/60 p-4">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">High-Level Summary</h4>
          <p className="mt-2 text-base text-slate-200">{decision.summary}</p>
        </section>

        <section className="rounded-xl border border-slate-800/70 bg-slate-950/60 p-4">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Confidence & Risk</h4>
          <div className="mt-2 flex flex-wrap gap-6 text-sm">
            <div>
              <span className="text-slate-500">Confidence:</span>
              <span className="ml-2 font-semibold text-white">{(decision.confidence * 100).toFixed(1)}%</span>
            </div>
            <div>
              <span className="text-slate-500">Risk Score:</span>
              <span className="ml-2 font-semibold text-white">{(decision.riskScore * 100).toFixed(0)} / 100</span>
            </div>
            <div>
              <span className="text-slate-500">Timestamp:</span>
              <span className="ml-2 font-semibold text-white">{new Date(decision.timestamp).toLocaleString()}</span>
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-slate-800/70 bg-slate-950/60 p-4">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Agent Debate</h4>
          <ul className="mt-2 space-y-3">
            {decision.agentInsights.map((insight) => (
              <li key={insight.agent} className="rounded-lg border border-slate-800/70 bg-slate-900/70 p-3">
                <div className="text-xs uppercase tracking-wide text-slate-500">{insight.agent}</div>
                <p className="mt-1 text-sm text-slate-200">{insight.statement}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-xl border border-slate-800/70 bg-slate-950/60 p-4">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Execution Plan</h4>
          <p className="mt-2 text-sm text-slate-200">{decision.rationale}</p>
        </section>
      </div>
    </div>
  );
}
