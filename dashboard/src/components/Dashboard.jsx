import { useMemo } from 'react'
import { TrendingUp, TrendingDown, Activity, BarChart3, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react'
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import './Dashboard.css'

function formatNumber(n) {
  if (n == null) return '-'
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B'
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return n.toLocaleString()
}

function formatPrice(p) {
  if (p == null) return '-'
  return p.toFixed(2)
}

const SIGNAL_COLORS = {
  'STRONG BUY': '#10b981',
  'BUY': '#34d399',
  'HOLD': '#6b7280',
  'SELL': '#f87171',
  'STRONG SELL': '#ef4444',
}

const SIGNAL_ORDER = ['STRONG BUY', 'BUY', 'HOLD', 'SELL', 'STRONG SELL']

export function Dashboard({ stocks, loading, onSelectStock }) {
  const stats = useMemo(() => {
    if (!stocks.length) return null

    const gainers = stocks.filter(s => (s['Change %'] ?? 0) > 0).length
    const losers = stocks.filter(s => (s['Change %'] ?? 0) < 0).length
    const unchanged = stocks.length - gainers - losers

    const avgChange = stocks.reduce((sum, s) => sum + (s['Change %'] ?? 0), 0) / stocks.length
    const totalVolume = stocks.reduce((sum, s) => sum + (s.Volume ?? 0), 0)
    const totalMarketCap = stocks.reduce((sum, s) => sum + (s['Market Cap'] ?? 0), 0)

    const signalCounts = {}
    stocks.forEach(s => {
      const sig = s.Signal || 'HOLD'
      signalCounts[sig] = (signalCounts[sig] || 0) + 1
    })
    const signalData = SIGNAL_ORDER
      .filter(s => signalCounts[s])
      .map(name => ({ name, value: signalCounts[name], color: SIGNAL_COLORS[name] }))

    const topGainers = [...stocks]
      .sort((a, b) => (b['Change %'] ?? 0) - (a['Change %'] ?? 0))
      .slice(0, 8)
    const topLosers = [...stocks]
      .sort((a, b) => (a['Change %'] ?? 0) - (b['Change %'] ?? 0))
      .slice(0, 8)

    const topVolume = [...stocks]
      .sort((a, b) => (b.Volume ?? 0) - (a.Volume ?? 0))
      .slice(0, 10)

    const rsiDistribution = [
      { range: '0-30', count: stocks.filter(s => (s['RSI 14'] ?? 50) < 30).length, color: '#10b981', label: 'Oversold' },
      { range: '30-70', count: stocks.filter(s => { const r = s['RSI 14'] ?? 50; return r >= 30 && r <= 70 }).length, color: '#6b7280', label: 'Neutral' },
      { range: '70-100', count: stocks.filter(s => (s['RSI 14'] ?? 50) > 70).length, color: '#ef4444', label: 'Overbought' },
    ]

    return { gainers, losers, unchanged, avgChange, totalVolume, totalMarketCap, signalData, topGainers, topLosers, topVolume, rsiDistribution }
  }, [stocks])

  if (loading || !stats) {
    return (
      <div className="dashboard">
        <div className="page-header">
          <h1>Dashboard</h1>
          <p>BIST Market Overview</p>
        </div>
        <div className="stats-grid">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="loading-skeleton stat-card" style={{ height: 100 }} />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>BIST Market Overview</p>
      </div>

      <div className="stats-grid">
        <StatCard
          title="Market Trend"
          icon={stats.avgChange >= 0 ? TrendingUp : TrendingDown}
          color={stats.avgChange >= 0 ? 'green' : 'red'}
        >
          <span className="stat-value">{stats.avgChange >= 0 ? '+' : ''}{stats.avgChange.toFixed(2)}%</span>
          <span className="stat-sub">avg change</span>
        </StatCard>

        <StatCard title="Gainers / Losers" icon={Activity} color="blue">
          <div className="gainer-loser">
            <span className="gl-up">{stats.gainers}</span>
            <span className="gl-sep">/</span>
            <span className="gl-down">{stats.losers}</span>
            <span className="gl-flat">({stats.unchanged})</span>
          </div>
        </StatCard>

        <StatCard title="Total Volume" icon={BarChart3} color="accent">
          <span className="stat-value">{formatNumber(stats.totalVolume)}</span>
        </StatCard>

        <StatCard title="Market Cap" icon={TrendingUp} color="yellow">
          <span className="stat-value">{formatNumber(stats.totalMarketCap)}</span>
          <span className="stat-sub">TRY</span>
        </StatCard>
      </div>

      <div className="charts-row">
        <div className="chart-card">
          <h3>Signal Distribution</h3>
          <div className="signal-chart-container">
            <div className="signal-pie-wrapper">
              <ResponsiveContainer width="100%" height={180}>
                <PieChart margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
                  <Pie
                    data={stats.signalData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={70}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {stats.signalData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#1e1f2b', border: '1px solid #2e303a', borderRadius: '8px', fontSize: '13px' }}
                    itemStyle={{ color: '#e4e5e9' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="signal-legend">
              {stats.signalData.map(({ name, value, color }) => (
                <div key={name} className="legend-item">
                  <span className="legend-dot" style={{ background: color }} />
                  <span className="legend-label">{name}</span>
                  <span className="legend-count">{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="chart-card">
          <h3>RSI Distribution</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={stats.rsiDistribution} barSize={40}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2e303a" />
              <XAxis dataKey="label" tick={{ fill: '#9ca3af', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: '#1e1f2b', border: '1px solid #2e303a', borderRadius: '8px', fontSize: '13px' }}
                itemStyle={{ color: '#e4e5e9' }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {stats.rsiDistribution.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Top Volume</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={stats.topVolume} layout="vertical" barSize={14}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2e303a" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={formatNumber} />
              <YAxis type="category" dataKey="Ticker" tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} width={80} tickFormatter={t => t.replace('.IS', '')} />
              <Tooltip
                contentStyle={{ background: '#1e1f2b', border: '1px solid #2e303a', borderRadius: '8px', fontSize: '13px' }}
                itemStyle={{ color: '#e4e5e9' }}
                formatter={(v) => formatNumber(v)}
              />
              <Bar dataKey="Volume" fill="#6366f1" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="movers-row">
        <div className="mover-card">
          <h3>
            <ArrowUpRight size={16} className="icon-green" />
            Top Gainers
          </h3>
          <div className="mover-list">
            {stats.topGainers.map(stock => (
              <button key={stock.Ticker} className="mover-item" onClick={() => onSelectStock(stock)}>
                <div className="mover-info">
                  <span className="mover-ticker">{stock.Ticker?.replace('.IS', '')}</span>
                  <span className="mover-price">{formatPrice(stock.Price)}</span>
                </div>
                <span className="mover-change positive">+{(stock['Change %'] ?? 0).toFixed(2)}%</span>
              </button>
            ))}
          </div>
        </div>

        <div className="mover-card">
          <h3>
            <ArrowDownRight size={16} className="icon-red" />
            Top Losers
          </h3>
          <div className="mover-list">
            {stats.topLosers.map(stock => (
              <button key={stock.Ticker} className="mover-item" onClick={() => onSelectStock(stock)}>
                <div className="mover-info">
                  <span className="mover-ticker">{stock.Ticker?.replace('.IS', '')}</span>
                  <span className="mover-price">{formatPrice(stock.Price)}</span>
                </div>
                <span className="mover-change negative">{(stock['Change %'] ?? 0).toFixed(2)}%</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ title, icon: Icon, color, children }) {
  return (
    <div className={`stat-card stat-${color}`}>
      <div className="stat-header">
        <span className="stat-title">{title}</span>
        <div className="stat-icon">
          <Icon size={18} />
        </div>
      </div>
      <div className="stat-body">
        {children}
      </div>
    </div>
  )
}
