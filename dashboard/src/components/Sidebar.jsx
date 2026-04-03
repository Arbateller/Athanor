import { LayoutDashboard, List, Zap, RefreshCw, TrendingUp, LineChart, ScanSearch, FlaskConical } from 'lucide-react'
import './Sidebar.css'

const NAV_ITEMS = [
  { id: 'dashboard',  label: 'Dashboard',   icon: LayoutDashboard },
  { id: 'stocks',     label: 'All Stocks',  icon: List },
  { id: 'signals',    label: 'Signals',     icon: Zap },
  { id: 'indicators', label: 'Indicators',  icon: LineChart },
  { id: 'scanner',    label: 'Scanner',     icon: ScanSearch },
  { id: 'simulation', label: 'Simulation',  icon: FlaskConical },
]

export function Sidebar({ view, onViewChange, lastUpdated, stockCount, onRefresh }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <TrendingUp size={22}/>
        <span className="brand-text">BIST Tracker</span>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={`nav-item ${view === id ? 'active' : ''}`}
            onClick={() => onViewChange(id)}
          >
            <Icon size={18}/>
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="status-info">
          <div className="status-row">
            <span className="status-dot"/>
            <span>{stockCount} stocks tracked</span>
          </div>
          {lastUpdated && (
            <div className="status-time">Updated {lastUpdated.toLocaleTimeString()}</div>
          )}
        </div>
        <button className="refresh-btn" onClick={onRefresh} title="Refresh now">
          <RefreshCw size={16}/>
        </button>
      </div>
    </aside>
  )
}
