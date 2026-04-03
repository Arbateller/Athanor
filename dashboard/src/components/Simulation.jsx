import { useState, useCallback } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine, Legend,
} from 'recharts'
import {
  Play, Plus, Trash2, RefreshCw, TrendingUp, TrendingDown,
  AlertCircle, CheckCircle, Info, ChevronDown, ChevronUp,
} from 'lucide-react'
import { runSimulation } from '../api'
import './Simulation.css'

// ─── HELPERS ──────────────────────────────────────────────────────────────────

function fmt(n, decimals = 2) {
  if (n == null) return '—'
  return parseFloat(n).toFixed(decimals)
}

function fmtMoney(n) {
  if (n == null) return '—'
  const v = parseFloat(n)
  if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(2) + 'M'
  if (Math.abs(v) >= 1e3) return (v / 1e3).toFixed(1) + 'K'
  return v.toFixed(2)
}

function PnlValue({ v, suffix = '' }) {
  if (v == null) return <span className="muted">—</span>
  const n = parseFloat(v)
  return (
    <span className={n > 0 ? 'pos' : n < 0 ? 'neg' : 'muted'}>
      {n > 0 ? '+' : ''}{fmtMoney(n)}{suffix}
    </span>
  )
}

const SIGNAL_CLASS = {
  'STRONG BUY':  'sig-strong-buy',
  'BUY':         'sig-buy',
  'SELL':        'sig-sell',
  'STRONG SELL': 'sig-strong-sell',
}

const SIGNAL_OPTIONS = ['STRONG BUY', 'BUY', 'SELL', 'STRONG SELL']

let _nextId = 1

// ─── METRIC CARD ──────────────────────────────────────────────────────────────

function MetricCard({ label, value, sub, color }) {
  return (
    <div className={`metric-card ${color || ''}`}>
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
      {sub && <span className="metric-sub">{sub}</span>}
    </div>
  )
}

// ─── MAIN COMPONENT ───────────────────────────────────────────────────────────

export function Simulation({ stocks }) {
  // Positions
  const [positions,   setPositions]   = useState([{ id: ++_nextId, ticker: '', buy_date: '', quantity: 1, sell_date: '' }])
  // Scanner rules for signal comparison
  const [scanRules,   setScanRules]   = useState([
    { id: ++_nextId, formula: 'RSI < 30', signal: 'BUY' },
    { id: ++_nextId, formula: 'RSI > 70', signal: 'SELL' },
  ])
  const [showRules,   setShowRules]   = useState(false)
  const [loading,     setLoading]     = useState(false)
  const [result,      setResult]      = useState(null)
  const [error,       setError]       = useState(null)

  // ── Position CRUD ─────────────────────────────────────────────────────────
  const addPosition = () =>
    setPositions(prev => [...prev, { id: ++_nextId, ticker: '', buy_date: '', quantity: 1, sell_date: '' }])

  const removePosition = id =>
    setPositions(prev => prev.filter(p => p.id !== id))

  const updatePosition = (id, field, val) =>
    setPositions(prev => prev.map(p => p.id === id ? { ...p, [field]: val } : p))

  // ── Rule CRUD ─────────────────────────────────────────────────────────────
  const addRule = () =>
    setScanRules(prev => [...prev, { id: ++_nextId, formula: '', signal: 'BUY' }])

  const removeRule = id =>
    setScanRules(prev => prev.filter(r => r.id !== id))

  const updateRule = (id, field, val) =>
    setScanRules(prev => prev.map(r => r.id === id ? { ...r, [field]: val } : r))

  // ── Run simulation ────────────────────────────────────────────────────────
  const run = useCallback(async () => {
    const validPositions = positions.filter(p => p.ticker && p.buy_date && p.quantity > 0)
    if (!validPositions.length) return

    setLoading(true); setError(null); setResult(null)
    try {
      const validRules = scanRules.filter(r => r.formula.trim())
      const data = await runSimulation({
        positions: validPositions.map(p => ({
          ticker:    p.ticker.toUpperCase().trim(),
          buy_date:  p.buy_date,
          quantity:  parseFloat(p.quantity),
          sell_date: p.sell_date || null,
        })),
        scan_rules: validRules.length ? validRules.map(r => ({ formula: r.formula, signal: r.signal })) : null,
      })
      setResult(data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }, [positions, scanRules])

  const isValid = positions.some(p => p.ticker && p.buy_date && p.quantity > 0)

  // ── Derived chart data ────────────────────────────────────────────────────
  const chartData   = result?.result?.series || []
  const isProfit    = (result?.result?.total_pnl || 0) >= 0
  const chartColor  = isProfit ? '#10b981' : '#ef4444'

  // For portfolio mode, also build per-position lines
  const isPortfolio = result?.mode === 'portfolio'
  const posResults  = result?.result?.positions || []

  // Tick formatter — show every Nth date to avoid crowding
  const tickInterval = chartData.length > 200 ? 'preserveStartEnd'
    : chartData.length > 60 ? Math.floor(chartData.length / 10)
    : 'preserveStartEnd'

  return (
    <div className="sim-page">
      <div className="page-header">
        <h1>Simulation</h1>
        <p>Backtest positions with real historical data</p>
      </div>

      <div className="sim-layout">

        {/* ── LEFT: Config ── */}
        <div className="sim-config">

          {/* Positions */}
          <div className="config-section">
            <div className="config-header">
              <span className="section-label">Positions</span>
              <button className="btn-sm btn-accent" onClick={addPosition}>
                <Plus size={12}/> Add
              </button>
            </div>

            <div className="positions-list">
              {positions.map((pos, idx) => (
                <div key={pos.id} className="position-card">
                  <div className="pos-header">
                    <span className="pos-num">#{idx + 1}</span>
                    {positions.length > 1 && (
                      <button className="btn-icon" onClick={() => removePosition(pos.id)}>
                        <Trash2 size={13}/>
                      </button>
                    )}
                  </div>

                  <div className="pos-fields">
                    {/* Ticker */}
                    <div className="pos-field">
                      <label>Ticker</label>
                      <input
                        list={`tickers-${pos.id}`}
                        className="pos-input ticker-input"
                        value={pos.ticker}
                        onChange={e => updatePosition(pos.id, 'ticker', e.target.value)}
                        placeholder="e.g. THYAO.IS"
                      />
                      <datalist id={`tickers-${pos.id}`}>
                        {stocks.slice(0, 50).map(s => (
                          <option key={s.Ticker} value={s.Ticker}>{s.Ticker?.replace('.IS', '')}</option>
                        ))}
                      </datalist>
                    </div>

                    {/* Quantity */}
                    <div className="pos-field small">
                      <label>Lots</label>
                      <input
                        className="pos-input"
                        type="number"
                        min={1}
                        value={pos.quantity}
                        onChange={e => updatePosition(pos.id, 'quantity', e.target.value)}
                      />
                    </div>

                    {/* Buy date */}
                    <div className="pos-field">
                      <label>Buy Date</label>
                      <input
                        className="pos-input"
                        type="date"
                        value={pos.buy_date}
                        onChange={e => updatePosition(pos.id, 'buy_date', e.target.value)}
                      />
                    </div>

                    {/* Sell date (optional) */}
                    <div className="pos-field">
                      <label>Sell Date <span className="optional">(optional)</span></label>
                      <input
                        className="pos-input"
                        type="date"
                        value={pos.sell_date}
                        onChange={e => updatePosition(pos.id, 'sell_date', e.target.value)}
                        min={pos.buy_date}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Signal comparison rules */}
          <div className="config-section">
            <button className="rules-toggle" onClick={() => setShowRules(r => !r)}>
              <Info size={13}/>
              <span>Signal comparison rules</span>
              {showRules ? <ChevronUp size={13}/> : <ChevronDown size={13}/>}
              <span className="rules-count">{scanRules.filter(r => r.formula).length} active</span>
            </button>

            {showRules && (
              <div className="rules-section">
                <p className="rules-hint">
                  These rules will be evaluated on your buy dates to show what signals were active when you "bought".
                </p>
                {scanRules.map(rule => (
                  <div key={rule.id} className="rule-row">
                    <select
                      className={`sig-select sig-sel-${rule.signal.toLowerCase().replace(/ /g, '-')}`}
                      value={rule.signal}
                      onChange={e => updateRule(rule.id, 'signal', e.target.value)}
                    >
                      {SIGNAL_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                    <input
                      className="formula-input"
                      value={rule.formula}
                      onChange={e => updateRule(rule.id, 'formula', e.target.value)}
                      placeholder="RSI < 30 AND MACD_HIST > 0"
                      spellCheck={false}
                    />
                    <button className="btn-icon" onClick={() => removeRule(rule.id)} disabled={scanRules.length <= 1}>
                      <Trash2 size={12}/>
                    </button>
                  </div>
                ))}
                <button className="btn-sm" onClick={addRule} style={{ alignSelf: 'flex-start' }}>
                  <Plus size={12}/> Add Rule
                </button>
              </div>
            )}
          </div>

          {/* Run button */}
          <button
            className={`run-btn ${loading ? 'loading' : ''}`}
            onClick={run}
            disabled={loading || !isValid}
          >
            {loading
              ? <><RefreshCw size={15} className="spin"/> Running simulation...</>
              : <><Play size={15}/> Run Simulation</>
            }
          </button>
        </div>

        {/* ── RIGHT: Results ── */}
        <div className="sim-results">

          {error && (
            <div className="sim-error"><AlertCircle size={15}/><span>{error}</span></div>
          )}

          {loading && (
            <div className="sim-empty">
              <RefreshCw size={28} className="spin"/>
              <p>Fetching historical data...</p>
            </div>
          )}

          {!result && !loading && !error && (
            <div className="sim-empty">
              <TrendingUp size={40} style={{ opacity: 0.15 }}/>
              <p>Configure your positions and run the simulation</p>
            </div>
          )}

          {result && !loading && (
            <>
              {/* ── Summary metrics ── */}
              <div className="metrics-grid">
                <MetricCard
                  label="Total Invested"
                  value={fmtMoney(result.result.cost_basis || result.result.total_cost)}
                  color=""
                />
                <MetricCard
                  label="Current Value"
                  value={fmtMoney(result.result.current_value)}
                  color={isProfit ? 'card-green' : 'card-red'}
                />
                <MetricCard
                  label="Total P&L"
                  value={<PnlValue v={result.result.total_pnl}/>}
                  sub={<PnlValue v={result.result.total_pnl_pct} suffix="%"/>}
                  color={isProfit ? 'card-green' : 'card-red'}
                />
                <MetricCard
                  label="Days Held"
                  value={result.result.days_held || result.result.days || '—'}
                  sub={result.result.buy_date ? `from ${result.result.buy_date}` : ''}
                />
                <MetricCard
                  label="Peak Value"
                  value={fmtMoney(result.result.peak_value)}
                  sub={result.result.peak_date}
                  color="card-blue"
                />
                <MetricCard
                  label="Max Drawdown"
                  value={`-${fmt(result.result.max_drawdown)}%`}
                  sub={result.result.low_date}
                  color={result.result.max_drawdown > 20 ? 'card-red' : ''}
                />
              </div>

              {/* ── Signal snapshot ── */}
              {result.snapshots?.length > 0 && (
                <div className="snapshot-section">
                  <h3>Signal Snapshot on Buy Date</h3>
                  <div className="snapshots">
                    {result.snapshots.map((snap, i) => (
                      <div key={i} className="snapshot-card">
                        <div className="snap-header">
                          <span className="snap-ticker">{snap.ticker?.replace('.IS', '')}</span>
                          <span className="snap-date">{snap.date}</span>
                          {snap.price_on_date && (
                            <span className="snap-price">@ {fmt(snap.price_on_date)}</span>
                          )}
                          {snap.signal
                            ? <span className={`signal-badge ${SIGNAL_CLASS[snap.signal] || ''}`}>{snap.signal}</span>
                            : snap.error
                              ? <span className="snap-error">No data</span>
                              : <span className="snap-none">No signal</span>
                          }
                        </div>
                        {snap.triggered_rules?.length > 0 && (
                          <div className="snap-rules">
                            {snap.triggered_rules.map((r, j) => (
                              <span key={j} className="snap-rule">
                                <span className={`signal-badge ${SIGNAL_CLASS[r.signal] || ''}`}>{r.signal}</span>
                                <code>{r.formula}</code>
                              </span>
                            ))}
                          </div>
                        )}
                        {snap.values && Object.keys(snap.values).length > 0 && (
                          <div className="snap-values">
                            {Object.entries(snap.values)
                              .filter(([k, v]) => v != null && !['VOLUME'].includes(k))
                              .map(([k, v]) => (
                                <span key={k} className="snap-val">
                                  <span className="snap-val-key">{k}</span>
                                  <span className="snap-val-num">{parseFloat(v).toFixed(2)}</span>
                                </span>
                              ))
                            }
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ── Portfolio value chart ── */}
              {chartData.length > 0 && (
                <div className="chart-card">
                  <h3>
                    {isPortfolio ? 'Portfolio Value' : `${result.result.ticker?.replace('.IS', '')} Position Value`}
                  </h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="simGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%"  stopColor={chartColor} stopOpacity={0.2}/>
                          <stop offset="95%" stopColor={chartColor} stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2e303a"/>
                      <XAxis dataKey="date" tick={{ fill:'#9ca3af', fontSize:11 }}
                             axisLine={false} tickLine={false} interval={tickInterval}/>
                      <YAxis tick={{ fill:'#9ca3af', fontSize:11 }} axisLine={false} tickLine={false}
                             tickFormatter={v => fmtMoney(v)} domain={['auto','auto']}/>
                      <Tooltip
                        contentStyle={{ background:'#1e1f2b', border:'1px solid #2e303a', borderRadius:'8px', fontSize:'12px' }}
                        itemStyle={{ color:'#e4e5e9' }}
                        labelStyle={{ color:'#9ca3af' }}
                        formatter={(v, name) => [fmtMoney(v), name]}
                      />
                      <ReferenceLine
                        y={result.result.cost_basis || result.result.total_cost}
                        stroke="#6b728060" strokeDasharray="4 2"
                        label={{ value:'Cost basis', position:'right', fill:'#6b7280', fontSize:11 }}
                      />
                      <Area type="monotone" dataKey="value" stroke={chartColor} strokeWidth={2}
                            fill="url(#simGrad)" dot={false} name="Portfolio Value"/>
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* ── P&L chart ── */}
              {chartData.length > 0 && (
                <div className="chart-card">
                  <h3>Daily P&L %</h3>
                  <ResponsiveContainer width="100%" height={180}>
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="pnlGradPos" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%"  stopColor="#10b981" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="pnlGradNeg" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%"  stopColor="#ef4444" stopOpacity={0}/>
                          <stop offset="95%" stopColor="#ef4444" stopOpacity={0.3}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2e303a"/>
                      <XAxis dataKey="date" tick={{ fill:'#9ca3af', fontSize:11 }}
                             axisLine={false} tickLine={false} interval={tickInterval}/>
                      <YAxis tick={{ fill:'#9ca3af', fontSize:11 }} axisLine={false} tickLine={false}
                             tickFormatter={v => v.toFixed(1) + '%'}/>
                      <Tooltip
                        contentStyle={{ background:'#1e1f2b', border:'1px solid #2e303a', borderRadius:'8px', fontSize:'12px' }}
                        itemStyle={{ color:'#e4e5e9' }}
                        formatter={v => [v.toFixed(2) + '%', 'P&L']}
                      />
                      <ReferenceLine y={0} stroke="#6b728060"/>
                      <Area type="monotone" dataKey="pnl_pct" stroke={isProfit ? '#10b981' : '#ef4444'}
                            strokeWidth={1.5} dot={false}
                            fill={isProfit ? 'url(#pnlGradPos)' : 'url(#pnlGradNeg)'}
                            name="P&L %"/>
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* ── Drawdown chart ── */}
              {chartData.length > 0 && (
                <div className="chart-card">
                  <h3>Drawdown %</h3>
                  <ResponsiveContainer width="100%" height={150}>
                    <AreaChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2e303a"/>
                      <XAxis dataKey="date" tick={{ fill:'#9ca3af', fontSize:11 }}
                             axisLine={false} tickLine={false} interval={tickInterval}/>
                      <YAxis tick={{ fill:'#9ca3af', fontSize:11 }} axisLine={false} tickLine={false}
                             tickFormatter={v => `-${Math.abs(v).toFixed(0)}%`}/>
                      <Tooltip
                        contentStyle={{ background:'#1e1f2b', border:'1px solid #2e303a', borderRadius:'8px', fontSize:'12px' }}
                        formatter={v => [`-${v.toFixed(2)}%`, 'Drawdown']}
                      />
                      <Area type="monotone" dataKey="drawdown" stroke="#ef4444" strokeWidth={1.5}
                            fill="rgba(239,68,68,0.1)" dot={false} name="Drawdown"/>
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* ── Per-position breakdown (portfolio mode) ── */}
              {isPortfolio && posResults.length > 0 && (
                <div className="breakdown-section">
                  <h3>Position Breakdown</h3>
                  <div className="breakdown-table-wrap">
                    <table className="breakdown-table">
                      <thead>
                        <tr>
                          <th>Ticker</th>
                          <th className="text-right">Buy Price</th>
                          <th className="text-right">Current</th>
                          <th className="text-right">Quantity</th>
                          <th className="text-right">Cost</th>
                          <th className="text-right">Value</th>
                          <th className="text-right">P&L</th>
                          <th className="text-right">P&L %</th>
                          <th className="text-right">Max DD</th>
                        </tr>
                      </thead>
                      <tbody>
                        {posResults.map(pos => (
                          <tr key={pos.ticker}>
                            <td className="bold">{pos.ticker?.replace('.IS', '')}</td>
                            <td className="text-right">{fmt(pos.buy_price)}</td>
                            <td className="text-right">{fmt(pos.current_price)}</td>
                            <td className="text-right">{pos.quantity}</td>
                            <td className="text-right">{fmtMoney(pos.cost_basis)}</td>
                            <td className="text-right">{fmtMoney(pos.current_value)}</td>
                            <td className="text-right"><PnlValue v={pos.total_pnl}/></td>
                            <td className="text-right"><PnlValue v={pos.total_pnl_pct} suffix="%"/></td>
                            <td className="text-right neg">-{fmt(pos.max_drawdown)}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
