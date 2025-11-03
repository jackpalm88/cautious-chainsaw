import { useDecisionStore } from '../../stores/decisionStore';
import ConfidenceGauge from './ConfidenceGauge';

export default function DecisionLogTable() {
  const { recentDecisions, selectDecision, selectedDecision } = useDecisionStore();

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">Latest Decisions</h3>
          <p className="text-xs uppercase tracking-wide text-slate-500">4-agent consensus with risk context</p>
        </div>
        {selectedDecision && (
          <div className="hidden sm:block">
            <ConfidenceGauge
              confidence={selectedDecision.confidence}
              title="Selected"
              subtitle={`${selectedDecision.action} ${selectedDecision.symbol}`}
              size="sm"
            />
          </div>
        )}
      </header>

      <div className="overflow-hidden rounded-xl border border-slate-800/80">
        <table className="min-w-full divide-y divide-slate-800 text-sm">
          <thead className="bg-slate-900/80 text-slate-400">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Timestamp</th>
              <th className="px-4 py-3 text-left font-medium">Symbol</th>
              <th className="px-4 py-3 text-left font-medium">Action</th>
              <th className="px-4 py-3 text-left font-medium">Summary</th>
              <th className="px-4 py-3 text-right font-medium">Confidence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 bg-slate-950/60 text-slate-300">
            {recentDecisions.map((decision) => {
              const isActive = selectedDecision?.id === decision.id;
              return (
                <tr
                  key={decision.id}
                  onClick={() => selectDecision(decision.id)}
                  className={`cursor-pointer transition hover:bg-slate-900/70 ${
                    isActive ? 'bg-slate-900/70' : ''
                  }`}
                >
                  <td className="px-4 py-2 text-xs text-slate-400">
                    {new Date(decision.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-2 font-medium text-white">{decision.symbol}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-semibold ${
                        decision.action === 'BUY'
                          ? 'bg-success/30 text-success'
                          : decision.action === 'SELL'
                          ? 'bg-danger/30 text-danger'
                          : 'bg-warning/30 text-warning'
                      }`}
                    >
                      {decision.action}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-sm">{decision.summary}</td>
                  <td className="px-4 py-2 text-right text-sm font-semibold text-slate-200">
                    {(decision.confidence * 100).toFixed(0)}%
                  </td>
                </tr>
              );
            })}
            {recentDecisions.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-slate-500">
                  No decisions ingested yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
