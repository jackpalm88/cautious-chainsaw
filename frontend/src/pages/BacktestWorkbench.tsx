import StrategySelector from '../components/Backtesting/StrategySelector';
import EquityCurveChart from '../components/Backtesting/EquityCurveChart';
import MetricsTable from '../components/Backtesting/MetricsTable';
import TradeListGrid from '../components/Backtesting/TradeListGrid';

export default function BacktestWorkbench() {
  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-white">Strategy Backtesting Workbench</h2>
          <p className="text-sm text-slate-400">Compare strategy performance, stress-test parameters and export trades.</p>
        </div>
        <StrategySelector />
      </header>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-lg shadow-slate-950/40 xl:col-span-2">
          <EquityCurveChart />
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-lg shadow-slate-950/40">
          <MetricsTable />
        </div>
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-lg shadow-slate-950/40">
        <TradeListGrid />
      </section>
    </div>
  );
}
