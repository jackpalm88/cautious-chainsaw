import { useMemo, useState } from 'react';
import { useBacktestStore } from '../../stores/backtestStore';

export default function TradeListGrid() {
  const { result } = useBacktestStore();
  const [filter, setFilter] = useState<'all' | 'winners' | 'losers'>('all');
  const [direction, setDirection] = useState<'all' | 'LONG' | 'SHORT'>('all');

  const trades = useMemo(() => {
    if (!result) return [];
    return result.trades.filter((trade) => {
      if (filter === 'winners' && trade.profit <= 0) return false;
      if (filter === 'losers' && trade.profit >= 0) return false;
      if (direction !== 'all' && trade.direction !== direction) return false;
      return true;
    });
  }, [result, filter, direction]);

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-white">Trade Ledger</h3>
          <p className="text-xs uppercase tracking-wide text-slate-500">Click a trade to highlight on chart</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <ToggleGroup
            label="P&L"
            options={[
              { id: 'all', label: 'All' },
              { id: 'winners', label: 'Winners' },
              { id: 'losers', label: 'Losers' }
            ]}
            value={filter}
            onChange={(value) => setFilter(value as typeof filter)}
          />
          <ToggleGroup
            label="Direction"
            options={[
              { id: 'all', label: 'All' },
              { id: 'LONG', label: 'Long' },
              { id: 'SHORT', label: 'Short' }
            ]}
            value={direction}
            onChange={(value) => setDirection(value as typeof direction)}
          />
        </div>
      </header>

      <div className="overflow-hidden rounded-xl border border-slate-800/80">
        <table className="min-w-full divide-y divide-slate-800 text-sm">
          <thead className="bg-slate-900/80 text-slate-400">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Entry</th>
              <th className="px-4 py-3 text-left font-medium">Exit</th>
              <th className="px-4 py-3 text-left font-medium">Direction</th>
              <th className="px-4 py-3 text-right font-medium">Profit ($)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 bg-slate-950/60 text-slate-300">
            {trades.map((trade) => (
              <tr key={trade.id} className="transition hover:bg-slate-900/70">
                <td className="px-4 py-2">{new Date(trade.entryTime).toLocaleString()}</td>
                <td className="px-4 py-2">{new Date(trade.exitTime).toLocaleString()}</td>
                <td className="px-4 py-2">
                  <span
                    className={`rounded-full px-2 py-1 text-xs font-semibold ${
                      trade.direction === 'LONG' ? 'bg-success/30 text-success' : 'bg-danger/30 text-danger'
                    }`}
                  >
                    {trade.direction}
                  </span>
                </td>
                <td className={`px-4 py-2 text-right ${trade.profit >= 0 ? 'text-success' : 'text-danger'}`}>
                  {trade.profit.toFixed(2)}
                </td>
              </tr>
            ))}
            {trades.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                  No trades match the selected filters yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

interface ToggleOption {
  id: string;
  label: string;
}

interface ToggleProps {
  label: string;
  options: ToggleOption[];
  value: string;
  onChange: (value: string) => void;
}

function ToggleGroup({ label, options, value, onChange }: ToggleProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-slate-500">{label}:</span>
      <div className="flex rounded-full border border-slate-800 bg-slate-900/80 p-1">
        {options.map((option) => {
          const active = option.id === value;
          return (
            <button
              key={option.id}
              type="button"
              onClick={() => onChange(option.id)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                active ? 'bg-slate-800 text-white shadow-inner' : 'text-slate-400 hover:text-white'
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
