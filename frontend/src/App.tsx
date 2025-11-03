import { NavLink, Route, Routes } from 'react-router-dom';
import LiveDashboard from './pages/LiveDashboard';
import BacktestWorkbench from './pages/BacktestWorkbench';
import SystemMonitor from './pages/SystemMonitor';

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
    isActive ? 'bg-slate-800 text-white' : 'text-slate-300 hover:text-white'
  }`;

function App() {
  return (
    <div className="min-h-screen bg-slate-950">
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-white">FinAgent Control Center</h1>
            <p className="text-sm text-slate-400">Monitor, diagnose and steer the trading agent in real-time.</p>
          </div>
          <nav className="flex items-center gap-2">
            <NavLink to="/" className={navLinkClass} end>
              Live Dashboard
            </NavLink>
            <NavLink to="/backtest" className={navLinkClass}>
              Backtesting
            </NavLink>
            <NavLink to="/system" className={navLinkClass}>
              Risk & Health
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-6">
        <Routes>
          <Route path="/" element={<LiveDashboard />} />
          <Route path="/backtest" element={<BacktestWorkbench />} />
          <Route path="/system" element={<SystemMonitor />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
