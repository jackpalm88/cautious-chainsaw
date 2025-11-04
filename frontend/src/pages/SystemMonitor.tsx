import ConfidenceGauge from '../components/INoT/ConfidenceGauge';
import DecisionDetailModal from '../components/INoT/DecisionDetailModal';
import { useDecisionStore } from '../stores/decisionStore';
import { useMemo } from 'react';

export default function SystemMonitor() {
  const { selectedDecision, recentDecisions } = useDecisionStore();
  const latest = useMemo(() => recentDecisions[0], [recentDecisions]);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-lg shadow-slate-950/40">
        <h2 className="text-2xl font-semibold text-white">INoT Decision Snapshot</h2>
        <p className="mt-1 text-sm text-slate-400">
          Inspect the latest agent consensus, uncertainty bands and debate transcript.
        </p>
        <div className="mt-8 flex flex-col gap-6 lg:flex-row">
          <ConfidenceGauge
            confidence={latest?.confidence ?? 0.5}
            title="Consensus Confidence"
            subtitle={latest ? latest.summary : 'Awaiting decision stream'}
          />
          <div className="flex-1 space-y-4 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <h3 className="text-lg font-semibold text-white">Reasoning Trace</h3>
            {latest ? (
              <ul className="space-y-3 text-sm text-slate-300">
                {latest.agentInsights.map((insight) => (
                  <li key={insight.agent} className="rounded-lg border border-slate-800/70 bg-slate-900/80 p-3">
                    <div className="text-xs uppercase tracking-wide text-slate-400">{insight.agent}</div>
                    <div className="text-sm">{insight.statement}</div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No decisions streamed yet.</p>
            )}
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-lg shadow-slate-950/40">
        <DecisionDetailModal decision={selectedDecision ?? latest ?? null} />
      </div>
    </div>
  );
}
