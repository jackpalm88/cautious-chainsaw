import { useEffect } from 'react';
import { useFusionStore } from '../stores/fusionStore';
import { useDecisionStore } from '../stores/decisionStore';
import PriceChartPanel from '../components/LiveDashboard/PriceChartPanel';
import SentimentPanel from '../components/LiveDashboard/SentimentPanel';
import EconomicEventsPanel from '../components/LiveDashboard/EconomicEventsPanel';
import SyncIndicator from '../components/LiveDashboard/SyncIndicator';
import DecisionLogTable from '../components/INoT/DecisionLogTable';
import PositionSizingCalculator from '../components/RiskControl/PositionSizingCalculator';
import EmergencyStopButton from '../components/RiskControl/EmergencyStopButton';

export default function LiveDashboard() {
  const connect = useFusionStore((state) => state.connect);
  const disconnect = useFusionStore((state) => state.disconnect);
  const connectionStatus = useFusionStore((state) => state.connectionStatus);
  const hydrateDecisions = useDecisionStore((state) => state.hydrate);

  useEffect(() => {
    connect('EURUSD');
    hydrateDecisions().catch((error) => {
      console.error('Failed to hydrate decisions', error);
    });
    return () => disconnect();
  }, [connect, disconnect, hydrateDecisions]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-white">Live Trading Dashboard</h2>
        <SyncIndicator status={connectionStatus} />
      </div>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="col-span-1 rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-lg shadow-slate-950/40 lg:col-span-2">
          <PriceChartPanel />
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-lg shadow-slate-950/40">
          <SentimentPanel />
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-lg shadow-slate-950/40 lg:col-span-2">
          <EconomicEventsPanel />
        </div>
        <div className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-lg shadow-slate-950/40">
          <PositionSizingCalculator />
          <EmergencyStopButton />
        </div>
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-lg shadow-slate-950/40">
        <DecisionLogTable />
      </section>
    </div>
  );
}
