import { useState, useEffect, useCallback } from 'react'
import {
  ComposedChart, Area, Line, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, ReferenceLine, Legend,
} from 'recharts'
import { Plus, X, ChevronDown, Loader, AlertCircle, Settings2 } from 'lucide-react'
import { fetchIndicators } from '../api'
import './IndicatorPanel.css'

// ─── CONFIG ───────────────────────────────────────────────────────────────────

const AVAILABLE_INDICATORS = [
  { id: 'RSI',       label: 'RSI (14)',            type: 'sub',     color: '#f59e0b' },
  { id: 'MACD',      label: 'MACD',                type: 'sub',     color: '#6366f1' },
  { id: 'BB',        label: 'Bollinger Bands',      type: 'overlay', color: '#8b5cf6' },
  { id: 'SMA',       label: 'SMA',                  type: 'overlay', color: '#f97316', hasParam: true, paramLabel: 'Period', paramKey: 'sma_period', defaultParam: 20 },
  { id: 'EMA',       label: 'EMA',                  type: 'overlay', color: '#06b6d4', hasParam: true, paramLabel: 'Period', paramKey: 'ema_period', defaultParam: 20 },
  { id: 'STOCH',     label: 'Stochastic',           type: 'sub',     color: '#ec4899' },
  { id: 'ATR',       label: 'ATR (14)',             type: 'sub',     color: '#10b981' },
  { id: 'FIBONACCI', label: 'Fibonacci Retracement', type: 'overlay', color: '#fbbf24' },
]

const PERIODS = [
  { value: '1mo', label: '1M' },
  { value: '3mo', label: '3M' },
  { value: '6mo', label: '6M' },
  { value: '1y',  label: '1Y' },
  { value: '2y',  label: '2Y' },
]

const FIB_COLORS = {
  '0.0':   '#ef4444',
  '0.236': '#f97316',
  '0.382': '#f59e0b',
  '0.5':   '#ffffff60',
  '0.618': '#10b981',
  '0.786': '#06b6d4',
  '1.0':   '#6366f1',
}

// ─── HELPERS ──────────────────────────────────────────────────────────────────

function fmt(n) {
  if (n == null) return '-'
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B'
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return n.toLocaleString()
}

// ─── MAIN COMPONENT ───────────────────────────────────────────────────────────

export function IndicatorPanel({ stocks }) {
  const [selectedTicker, setSelectedTicker] = useState('')
  const [tickerSearch,   setTickerSearch]   = useState('')
  const [showDropdown,   setShowDropdown]   = useState(false)
  const [activeInds,     setActiveInds]     = useState([])   // { id, params }
  const [period,         setPeriod]         = useState('3mo')
  const [data,           setData]           = useState(null)
  const [loading,        setLoading]        = useState(false)
  const [error,          setError]          = useState(null)
  const [paramValues,    setParamValues]    = useState({})   // { sma_period: 20, ema_period: 20 }

  const filteredStocks = stocks.filter(s =>
    s.Ticker?.toLowerCase().includes(tickerSearch.toLowerCase()) ||
    s.Name?.toLowerCase().includes(tickerSearch.toLowerCase())
  ).slice(0, 20)

  // ── Fetch data when ticker / indicators / period change ───────────────────
  const load = useCallback(async () => {
    if (!selectedTicker || activeInds.length === 0) return
    setLoading(true)
    setError(null)
    try {
      const ids = activeInds.map(a => a.id)
      const result = await fetchIndicators(selectedTicker, ids, {
        period,
        sma_period: paramValues.sma_period || 20,
        ema_period: paramValues.ema_period || 20,
      })
      // Merge indicator values into the OHLCV rows
      const merged = result.data.map((row, i) => {
        const merged = { ...row }
        const inds   = result.indicators

        if (inds.RSI)    merged.rsi       = inds.RSI.values[i]
        if (inds.MACD) {
          merged.macd_line   = inds.MACD.macd[i]
          merged.macd_signal = inds.MACD.signal[i]
          merged.macd_hist   = inds.MACD.histogram[i]
        }
        if (inds.BB) {
          merged.bb_upper  = inds.BB.upper[i]
          merged.bb_middle = inds.BB.middle[i]
          merged.bb_lower  = inds.BB.lower[i]
        }
        if (inds.SMA)   merged.sma        = inds.SMA.values[i]
        if (inds.EMA)   merged.ema        = inds.EMA.values[i]
        if (inds.STOCH) {
          merged.stoch_k = inds.STOCH.k[i]
          merged.stoch_d = inds.STOCH.d[i]
        }
        if (inds.ATR)   merged.atr        = inds.ATR.values[i]
        return merged
      })
      setData({ ...result, merged, fibLevels: result.indicators.FIBONACCI?.levels || null })
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }, [selectedTicker, activeInds, period, paramValues])

  useEffect(() => { load() }, [load])

  // ── Add / remove indicator ─────────────────────────────────────────────────
  const addIndicator = (ind) => {
    if (activeInds.find(a => a.id === ind.id)) return
    setActiveInds(prev => [...prev, { id: ind.id }])
    if (ind.hasParam) {
      setParamValues(prev => ({ ...prev, [ind.paramKey]: ind.defaultParam }))
    }
  }

  const removeIndicator = (id) => {
    setActiveInds(prev => prev.filter(a => a.id !== id))
  }

  // ── Chart color based on price trend ──────────────────────────────────────
  const chartColor = data?.merged?.length >= 2
    ? (data.merged[data.merged.length - 1].close >= data.merged[0].close ? '#10b981' : '#ef4444')
    : '#6366f1'

  const overlayInds = activeInds.filter(a => AVAILABLE_INDICATORS.find(x => x.id === a.id)?.type === 'overlay' && a.id !== 'FIBONACCI')
  const subInds     = activeInds.filter(a => AVAILABLE_INDICATORS.find(x => x.id === a.id)?.type === 'sub')
  const hasFib      = activeInds.some(a => a.id === 'FIBONACCI')

  const tickerDisplay = selectedTicker?.replace('.IS', '')

  return (
    <div className="indicator-panel">
      {/* ── Header ── */}
      <div className="page-header">
        <h1>Indicators</h1>
        <p>Select a stock and add technical indicators</p>
      </div>

      {/* ── Controls bar ── */}
      <div className="ind-controls">

        {/* Ticker selector */}
        <div className="ticker-selector" onBlur={() => setTimeout(() => setShowDropdown(false), 150)}>
          <div className="ticker-input-wrap" onClick={() => setShowDropdown(true)}>
            <input
              className="ticker-input"
              placeholder="Search ticker..."
              value={tickerSearch || selectedTicker}
              onChange={e => { setTickerSearch(e.target.value); setShowDropdown(true) }}
              onFocus={() => setShowDropdown(true)}
            />
            <ChevronDown size={15} className="ticker-chevron" />
          </div>
          {showDropdown && filteredStocks.length > 0 && (
            <div className="ticker-dropdown">
              {filteredStocks.map(s => (
                <button
                  key={s.Ticker}
                  className="ticker-option"
                  onClick={() => {
                    setSelectedTicker(s.Ticker)
                    setTickerSearch('')
                    setShowDropdown(false)
                  }}
                >
                  <span className="to-ticker">{s.Ticker?.replace('.IS', '')}</span>
                  <span className="to-price">{s.Price?.toFixed(2)}</span>
                  <span className={`to-change ${s['Change %'] >= 0 ? 'pos' : 'neg'}`}>
                    {s['Change %'] >= 0 ? '+' : ''}{s['Change %']?.toFixed(2)}%
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Period tabs */}
        <div className="period-tabs">
          {PERIODS.map(p => (
            <button
              key={p.value}
              className={`period-tab ${period === p.value ? 'active' : ''}`}
              onClick={() => setPeriod(p.value)}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Add indicator dropdown */}
        <IndicatorPicker activeInds={activeInds} onAdd={addIndicator} />
      </div>

      {/* ── Active indicator chips ── */}
      {activeInds.length > 0 && (
        <div className="ind-chips">
          {activeInds.map(a => {
            const meta = AVAILABLE_INDICATORS.find(x => x.id === a.id)
            return (
              <div key={a.id} className="ind-chip" style={{ borderColor: meta?.color }}>
                <span className="chip-dot" style={{ background: meta?.color }} />
                <span className="chip-label">{meta?.label}</span>
                {meta?.hasParam && (
                  <input
                    className="chip-param"
                    type="number"
                    min={2}
                    max={200}
                    value={paramValues[meta.paramKey] || meta.defaultParam}
                    onChange={e => setParamValues(prev => ({ ...prev, [meta.paramKey]: Number(e.target.value) }))}
                  />
                )}
                <button className="chip-remove" onClick={() => removeIndicator(a.id)}>
                  <X size={12} />
                </button>
              </div>
            )
          })}
        </div>
      )}

      {/* ── States ── */}
      {!selectedTicker && (
        <div className="ind-empty">
          <Settings2 size={40} className="empty-icon" />
          <p>Select a stock to get started</p>
        </div>
      )}

      {selectedTicker && activeInds.length === 0 && (
        <div className="ind-empty">
          <Plus size={40} className="empty-icon" />
          <p>Add an indicator using the button above</p>
        </div>
      )}

      {error && (
        <div className="ind-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {loading && (
        <div className="ind-loading">
          <Loader size={24} className="spin" />
          <span>Computing indicators...</span>
        </div>
      )}

      {/* ── Charts ── */}
      {!loading && data && (
        <div className="charts-container">

          {/* Price + overlays */}
          <div className="chart-card main-chart">
            <h3>
              {tickerDisplay} — Price
              {overlayInds.map(a => {
                const meta = AVAILABLE_INDICATORS.find(x => x.id === a.id)
                return <span key={a.id} className="chart-badge" style={{ color: meta?.color }}>{meta?.label}</span>
              })}
              {hasFib && <span className="chart-badge" style={{ color: '#fbbf24' }}>Fibonacci</span>}
            </h3>
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={data.merged}>
                <defs>
                  <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={chartColor} stopOpacity={0.2} />
                    <stop offset="95%" stopColor={chartColor} stopOpacity={0}   />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#2e303a" />
                <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                <YAxis domain={['auto', 'auto']} tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: '#1e1f2b', border: '1px solid #2e303a', borderRadius: '8px', fontSize: '12px' }}
                  itemStyle={{ color: '#e4e5e9' }}
                  labelStyle={{ color: '#9ca3af' }}
                />
                <Area type="monotone" dataKey="close" stroke={chartColor} strokeWidth={2} fill="url(#priceGrad)" dot={false} name="Price" />
                {activeInds.some(a => a.id === 'BB') && <>
                  <Line type="monotone" dataKey="bb_upper"  stroke="#8b5cf6" strokeWidth={1} dot={false} strokeDasharray="4 2" name="BB Upper" />
                  <Line type="monotone" dataKey="bb_middle" stroke="#8b5cf680" strokeWidth={1} dot={false} strokeDasharray="4 2" name="BB Mid" />
                  <Line type="monotone" dataKey="bb_lower"  stroke="#8b5cf6" strokeWidth={1} dot={false} strokeDasharray="4 2" name="BB Lower" />
                </>}
                {activeInds.some(a => a.id === 'SMA') && (
                  <Line type="monotone" dataKey="sma" stroke="#f97316" strokeWidth={1.5} dot={false} name={`SMA ${paramValues.sma_period || 20}`} />
                )}
                {activeInds.some(a => a.id === 'EMA') && (
                  <Line type="monotone" dataKey="ema" stroke="#06b6d4" strokeWidth={1.5} dot={false} name={`EMA ${paramValues.ema_period || 20}`} />
                )}
                {hasFib && data.fibLevels && Object.entries(data.fibLevels).map(([level, price]) => (
                  <ReferenceLine key={level} y={price} stroke={FIB_COLORS[level] || '#ffffff40'} strokeDasharray="4 2" strokeWidth={1}
                    label={{ value: `${level} (${price})`, position: 'right', fill: FIB_COLORS[level] || '#9ca3af', fontSize: 10 }}
                  />
                ))}
                <Legend wrapperStyle={{ fontSize: '12px', color: '#9ca3af' }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* RSI sub-chart */}
          {activeInds.some(a => a.id === 'RSI') && (
            <div className="chart-card sub-chart">
              <h3>RSI (14)</h3>
              <ResponsiveContainer width="100%" height={160}>
                <ComposedChart data={data.merged}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2e303a" />
                  <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                  <YAxis domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: '#1e1f2b', border: '1px solid #2e303a', borderRadius: '8px', fontSize: '12px' }} itemStyle={{ color: '#e4e5e9' }} />
                  <ReferenceLine y={70} stroke="#ef444460" strokeDasharray="4 2" />
                  <ReferenceLine y={30} stroke="#10b98160" strokeDasharray="4 2" />
                  <Line type="monotone" dataKey="rsi" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="RSI" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* MACD sub-chart */}
          {activeInds.some(a => a.id === 'MACD') && (
            <div className="chart-card sub-chart">
              <h3>MACD</h3>
              <ResponsiveContainer width="100%" height={180}>
                <ComposedChart data={data.merged}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2e303a" />
                  <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                  <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: '#1e1f2b', border: '1px solid #2e303a', borderRadius: '8px', fontSize: '12px' }} itemStyle={{ color: '#e4e5e9' }} />
                  <ReferenceLine y={0} stroke="#ffffff20" />
                  <Bar dataKey="macd_hist" name="Histogram" radius={[2, 2, 0, 0]}
                    fill="#6366f1"
                    label={false}
                  />
                  <Line type="monotone" dataKey="macd_line"   stroke="#6366f1" strokeWidth={1.5} dot={false} name="MACD"   />
                  <Line type="monotone" dataKey="macd_signal" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="Signal" />
                  <Legend wrapperStyle={{ fontSize: '12px', color: '#9ca3af' }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Stochastic sub-chart */}
          {activeInds.some(a => a.id === 'STOCH') && (
            <div className="chart-card sub-chart">
              <h3>Stochastic</h3>
              <ResponsiveContainer width="100%" height={160}>
                <ComposedChart data={data.merged}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2e303a" />
                  <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                  <YAxis domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: '#1e1f2b', border: '1px solid #2e303a', borderRadius: '8px', fontSize: '12px' }} itemStyle={{ color: '#e4e5e9' }} />
                  <ReferenceLine y={80} stroke="#ef444460" strokeDasharray="4 2" />
                  <ReferenceLine y={20} stroke="#10b98160" strokeDasharray="4 2" />
                  <Line type="monotone" dataKey="stoch_k" stroke="#ec4899" strokeWidth={1.5} dot={false} name="%K" />
                  <Line type="monotone" dataKey="stoch_d" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="%D" />
                  <Legend wrapperStyle={{ fontSize: '12px', color: '#9ca3af' }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* ATR sub-chart */}
          {activeInds.some(a => a.id === 'ATR') && (
            <div className="chart-card sub-chart">
              <h3>ATR (14) — Average True Range</h3>
              <ResponsiveContainer width="100%" height={140}>
                <ComposedChart data={data.merged}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2e303a" />
                  <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                  <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: '#1e1f2b', border: '1px solid #2e303a', borderRadius: '8px', fontSize: '12px' }} itemStyle={{ color: '#e4e5e9' }} />
                  <Line type="monotone" dataKey="atr" stroke="#10b981" strokeWidth={1.5} dot={false} name="ATR" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Fibonacci table */}
          {hasFib && data.fibLevels && (
            <div className="chart-card fib-card">
              <h3>Fibonacci Retracement Levels</h3>
              <div className="fib-table">
                {Object.entries(data.fibLevels).map(([level, price]) => (
                  <div key={level} className="fib-row">
                    <span className="fib-dot" style={{ background: FIB_COLORS[level] }} />
                    <span className="fib-level">{(parseFloat(level) * 100).toFixed(1)}%</span>
                    <span className="fib-price">{price.toFixed(4)}</span>
                    <div className="fib-bar-wrap">
                      <div
                        className="fib-bar"
                        style={{
                          width: `${100 - parseFloat(level) * 100}%`,
                          background: FIB_COLORS[level],
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <p className="fib-note">Range: {data.fibLevels['1.0']?.toFixed(2)} – {data.fibLevels['0.0']?.toFixed(2)}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}


// ─── INDICATOR PICKER ─────────────────────────────────────────────────────────

function IndicatorPicker({ activeInds, onAdd }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="ind-picker" onBlur={() => setTimeout(() => setOpen(false), 150)}>
      <button className="add-ind-btn" onClick={() => setOpen(o => !o)}>
        <Plus size={15} />
        Add Indicator
        <ChevronDown size={13} />
      </button>
      {open && (
        <div className="ind-dropdown">
          {AVAILABLE_INDICATORS.map(ind => {
            const active = activeInds.some(a => a.id === ind.id)
            return (
              <button
                key={ind.id}
                className={`ind-option ${active ? 'active' : ''}`}
                onClick={() => { onAdd(ind); setOpen(false) }}
              >
                <span className="ind-dot" style={{ background: ind.color }} />
                <span className="ind-name">{ind.label}</span>
                <span className="ind-type">{ind.type}</span>
                {active && <span className="ind-check">✓</span>}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
