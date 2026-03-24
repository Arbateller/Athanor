import { useState, useCallback, useRef } from 'react'
import { Play, RefreshCw, Plus, Trash2, AlertCircle, Clock, Info, ChevronDown, ChevronUp } from 'lucide-react'
import { runScanner } from '../api'
import './SignalScanner.css'

// ─── CONFIG ───────────────────────────────────────────────────────────────────

const SIGNAL_OPTIONS  = ['STRONG BUY', 'BUY', 'SELL', 'STRONG SELL']
const SIGNAL_PRIORITY = { 'STRONG BUY': 5, 'BUY': 4, 'SELL': 2, 'STRONG SELL': 1 }
const SIGNAL_CLASS    = {
  'STRONG BUY':  'sig-strong-buy',
  'BUY':         'sig-buy',
  'SELL':        'sig-sell',
  'STRONG SELL': 'sig-strong-sell',
}
const PERIODS = ['1mo', '3mo', '6mo', '1y']

const VARIABLES = [
  'RSI', 'MACD_LINE', 'MACD_SIGNAL', 'MACD_HIST',
  'BB_UPPER', 'BB_MIDDLE', 'BB_LOWER',
  'SMA', 'EMA', 'STOCH_K', 'STOCH_D', 'ATR',
  'PRICE', 'CHANGE_PCT', 'VOLUME',
]

const PRESET_SETS = [
  { label: 'Classic RSI', rules: [
    { formula: 'RSI < 25', signal: 'STRONG BUY' },
    { formula: 'RSI < 35', signal: 'BUY' },
    { formula: 'RSI > 65', signal: 'SELL' },
    { formula: 'RSI > 75', signal: 'STRONG SELL' },
  ]},
  { label: 'RSI + MACD', rules: [
    { formula: 'RSI < 30 AND MACD_HIST > 0', signal: 'STRONG BUY' },
    { formula: 'RSI < 40 AND MACD_HIST > 0', signal: 'BUY' },
    { formula: 'RSI > 60 AND MACD_HIST < 0', signal: 'SELL' },
    { formula: 'RSI > 70 AND MACD_HIST < 0', signal: 'STRONG SELL' },
  ]},
  { label: 'Bollinger Bands', rules: [
    { formula: 'PRICE < BB_LOWER AND RSI < 35', signal: 'STRONG BUY' },
    { formula: 'PRICE < BB_LOWER', signal: 'BUY' },
    { formula: 'PRICE > BB_UPPER', signal: 'SELL' },
    { formula: 'PRICE > BB_UPPER AND RSI > 65', signal: 'STRONG SELL' },
  ]},
  { label: 'Stochastic', rules: [
    { formula: 'STOCH_K < 15 AND STOCH_D < 15', signal: 'STRONG BUY' },
    { formula: 'STOCH_K < 25', signal: 'BUY' },
    { formula: 'STOCH_K > 75', signal: 'SELL' },
    { formula: 'STOCH_K > 85 AND STOCH_D > 85', signal: 'STRONG SELL' },
  ]},
  { label: 'Full Combo', rules: [
    { formula: 'RSI < 28 AND MACD_HIST > 0 AND STOCH_K < 25', signal: 'STRONG BUY' },
    { formula: 'RSI < 38 AND MACD_HIST > 0', signal: 'BUY' },
    { formula: 'RSI > 62 AND MACD_HIST < 0', signal: 'SELL' },
    { formula: 'RSI > 72 AND MACD_HIST < 0 AND STOCH_K > 75', signal: 'STRONG SELL' },
  ]},
]

const DEFAULT_RULES = [
  { id: 1, formula: 'RSI < 25', signal: 'STRONG BUY'  },
  { id: 2, formula: 'RSI < 35', signal: 'BUY'         },
  { id: 3, formula: 'RSI > 65', signal: 'SELL'        },
  { id: 4, formula: 'RSI > 75', signal: 'STRONG SELL' },
]

let _nextId = 10

// ─── HELPERS ──────────────────────────────────────────────────────────────────

function SignalBadge({ signal }) {
  if (!signal) return <span className="sig-none">—</span>
  return <span className={`signal-badge ${SIGNAL_CLASS[signal] || ''}`}>{signal}</span>
}

function PctCell({ v }) {
  if (v == null) return <span className="val-null">—</span>
  const n = parseFloat(v)
  return <span className={n >= 0 ? 'val-pos' : 'val-neg'}>{n >= 0 ? '+' : ''}{n.toFixed(2)}%</span>
}

function NumCell({ v, decimals = 2 }) {
  if (v == null) return <span className="val-null">—</span>
  const n = parseFloat(v)
  const cls = n < 30 && decimals === 1 ? 'rsi-low' : n > 70 && decimals === 1 ? 'rsi-high' : ''
  return <span className={cls}>{n.toFixed(decimals)}</span>
}

// ─── MAIN ─────────────────────────────────────────────────────────────────────

export function SignalScanner() {
  const [rules,       setRules]       = useState(DEFAULT_RULES)
  const [period,      setPeriod]      = useState('3mo')
  const [smaPeriod,   setSmaPeriod]   = useState(20)
  const [emaPeriod,   setEmaPeriod]   = useState(20)
  const [loading,     setLoading]     = useState(false)
  const [result,      setResult]      = useState(null)
  const [error,       setError]       = useState(null)
  const [filter,      setFilter]      = useState('all')
  const [showGuide,   setShowGuide]   = useState(false)
  const [showPresets, setShowPresets] = useState(false)
  const [sortKey,     setSortKey]     = useState('priority')
  const [sortDir,     setSortDir]     = useState('desc')
  const [expanded,    setExpanded]    = useState(null)
  const inputRefs = useRef({})

  // ── Rules ─────────────────────────────────────────────────────────────────
  const addRule = () => setRules(prev => [...prev, { id: ++_nextId, formula: '', signal: 'BUY' }])
  const removeRule = id => setRules(prev => prev.filter(r => r.id !== id))
  const updateRule = (id, field, val) => setRules(prev => prev.map(r => r.id === id ? {...r, [field]: val} : r))
  const loadPreset = preset => { setRules(preset.rules.map(r => ({...r, id: ++_nextId}))); setShowPresets(false) }

  const insertVar = (id, varName) => {
    const el = inputRefs.current[id]
    const cur = rules.find(r => r.id === id)?.formula || ''
    if (!el) { updateRule(id, 'formula', cur + ' ' + varName); return }
    const s = el.selectionStart, e = el.selectionEnd
    updateRule(id, 'formula', cur.slice(0, s) + varName + cur.slice(e))
    setTimeout(() => { el.selectionStart = el.selectionEnd = s + varName.length; el.focus() }, 0)
  }

  // ── Scan ──────────────────────────────────────────────────────────────────
  const scan = useCallback(async () => {
    const valid = rules.filter(r => r.formula.trim())
    if (!valid.length) return
    setLoading(true); setError(null)
    try {
      const data = await runScanner({
        rules:      valid.map(r => ({ formula: r.formula.trim(), signal: r.signal })),
        period,
        sma_period: smaPeriod,
        ema_period: emaPeriod,
      })
      setResult(data)
      setFilter('all')
      setExpanded(null)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }, [rules, period, smaPeriod, emaPeriod])

  // ── Sort / filter ─────────────────────────────────────────────────────────
  const handleSort = key => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const filteredRows = result?.results
    ? result.results.filter(r => {
        if (filter === 'triggered') return r.signal != null
        if (filter === 'nosignal')  return r.signal == null && !r.error
        if (filter === 'errors')    return !!r.error
        return true
      })
    : []

  const sortedRows = [...filteredRows].sort((a, b) => {
    let av = a[sortKey], bv = b[sortKey]
    if (sortKey === 'rsi')       { av = a.values?.RSI;       bv = b.values?.RSI }
    if (sortKey === 'macd_hist') { av = a.values?.MACD_HIST; bv = b.values?.MACD_HIST }
    if (av == null) return 1; if (bv == null) return -1
    if (typeof av === 'string') { const c = av.localeCompare(bv); return sortDir === 'asc' ? c : -c }
    return sortDir === 'asc' ? av - bv : bv - av
  })

  // Which columns to show
  const formulaText = rules.map(r => r.formula).join(' ')
  const showRSI   = /\bRSI\b/.test(formulaText)
  const showMACD  = /\bMACD/.test(formulaText)
  const showStoch = /\bSTOCH/.test(formulaText)
  const showBB    = /\bBB_/.test(formulaText)
  const showSMA   = /\bSMA\b/.test(formulaText)
  const showEMA   = /\bEMA\b/.test(formulaText)

  const SortTh = ({ label, k, align }) => {
    const cls = [align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : '', 'th-sort'].join(' ')
    return (
      <th className={cls} onClick={() => handleSort(k)}>
        {label}{sortKey === k ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''}
      </th>
    )
  }

  // Flatten rows: for each data row, optionally append an expanded detail row
  const tableRows = []
  sortedRows.forEach(row => {
    tableRows.push({ type: 'data', row })
    if (expanded === row.ticker && row.triggered_rules?.length > 0) {
      tableRows.push({ type: 'expanded', row })
    }
  })

  return (
    <div className="scanner-page">
      <div className="page-header">
        <h1>Signal Scanner</h1>
        <p>Define rules for each signal level — strongest match wins</p>
      </div>

      <div className="scanner-layout">

        {/* ── LEFT: Editor ── */}
        <div className="scanner-editor">

          {/* Rules */}
          <div className="rules-section">
            <div className="rules-header">
              <span className="section-label">Rules</span>
              <div className="rules-actions">
                <button className="btn-sm" onClick={() => setShowPresets(p => !p)}>
                  Presets {showPresets ? <ChevronUp size={12}/> : <ChevronDown size={12}/>}
                </button>
                <button className="btn-sm btn-accent" onClick={addRule}>
                  <Plus size={12}/> Add
                </button>
              </div>
            </div>

            {showPresets && (
              <div className="presets-list">
                {PRESET_SETS.map(ps => (
                  <button key={ps.label} className="preset-item" onClick={() => loadPreset(ps)}>
                    <span>{ps.label}</span>
                    <span className="preset-count">{ps.rules.length} rules</span>
                  </button>
                ))}
              </div>
            )}

            <div className="rules-list">
              {rules.map((rule, idx) => (
                <div key={rule.id} className="rule-row">
                  <span className="rule-num">{idx + 1}</span>
                  <select
                    className={`sig-select sig-sel-${rule.signal.toLowerCase().replace(/ /g, '-')}`}
                    value={rule.signal}
                    onChange={e => updateRule(rule.id, 'signal', e.target.value)}
                  >
                    {SIGNAL_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                  <input
                    ref={el => { inputRefs.current[rule.id] = el }}
                    className="formula-input"
                    value={rule.formula}
                    onChange={e => updateRule(rule.id, 'formula', e.target.value)}
                    placeholder="e.g. RSI < 30 AND MACD_HIST > 0"
                    spellCheck={false}
                  />
                  <button
                    className="btn-icon"
                    onClick={() => removeRule(rule.id)}
                    disabled={rules.length <= 1}
                  >
                    <Trash2 size={13}/>
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Variable guide */}
          <div className="guide-section">
            <button className="guide-toggle" onClick={() => setShowGuide(g => !g)}>
              <Info size={12}/> Variables {showGuide ? <ChevronUp size={11}/> : <ChevronDown size={11}/>}
            </button>
            {showGuide && (
              <div className="guide-body">
                <p className="guide-ops">Operators: &lt; &gt; &lt;= &gt;= == AND OR</p>
                <div className="var-chips">
                  {VARIABLES.map(v => (
                    <button
                      key={v}
                      className="var-chip"
                      onClick={() => {
                        const active = Object.entries(inputRefs.current)
                          .find(([, el]) => el === document.activeElement)
                        if (active) insertVar(Number(active[0]), v)
                        else if (rules.length > 0) insertVar(rules[rules.length - 1].id, v)
                      }}
                    >
                      {v}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Options */}
          <div className="options-section">
            <div className="option-field">
              <label className="option-label">Period</label>
              <div className="period-btns">
                {PERIODS.map(p => (
                  <button key={p} className={`period-btn ${period === p ? 'active' : ''}`} onClick={() => setPeriod(p)}>
                    {p}
                  </button>
                ))}
              </div>
            </div>
            <div className="option-row">
              <div className="option-field">
                <label className="option-label">SMA Period</label>
                <input className="param-input" type="number" min={2} max={200} value={smaPeriod} onChange={e => setSmaPeriod(Number(e.target.value))}/>
              </div>
              <div className="option-field">
                <label className="option-label">EMA Period</label>
                <input className="param-input" type="number" min={2} max={200} value={emaPeriod} onChange={e => setEmaPeriod(Number(e.target.value))}/>
              </div>
            </div>
          </div>

          <button
            className={`run-btn ${loading ? 'loading' : ''}`}
            onClick={scan}
            disabled={loading || !rules.some(r => r.formula.trim())}
          >
            {loading
              ? <><RefreshCw size={15} className="spin"/> Scanning...</>
              : <><Play size={15}/> Run Scanner</>
            }
          </button>
        </div>

        {/* ── RIGHT: Results ── */}
        <div className="scanner-results">

          {error && (
            <div className="scan-error">
              <AlertCircle size={15}/>
              <span>{error}</span>
            </div>
          )}

          {loading && !result && (
            <div className="scan-empty">
              <RefreshCw size={28} className="spin"/>
              <p>Scanning all stocks...</p>
              <p className="scan-note">May take 20–60s for large watchlists</p>
            </div>
          )}

          {!result && !loading && !error && (
            <div className="scan-empty">
              <Play size={36} style={{ opacity: 0.2 }}/>
              <p>Configure your rules and click Run Scanner</p>
            </div>
          )}

          {result && (
            <>
              {/* Summary */}
              <div className="summary-bar">
                <div className="sum-badges">
                  {['STRONG BUY', 'BUY', 'SELL', 'STRONG SELL'].map(sig => {
                    const cnt = result.signal_counts?.[sig] || 0
                    if (!cnt) return null
                    return (
                      <span key={sig} className={`sum-badge ${SIGNAL_CLASS[sig]}`}>
                        {sig} <strong>{cnt}</strong>
                      </span>
                    )
                  })}
                  {result.triggered_count === 0 && (
                    <span className="sum-none">No signals triggered</span>
                  )}
                </div>
                <div className="sum-meta">
                  <span>{result.total} stocks scanned</span>
                  <Clock size={12}/>
                  <span>{result.elapsed}s</span>
                  <button className="btn-sm" onClick={scan} disabled={loading}>
                    <RefreshCw size={12} className={loading ? 'spin' : ''}/> Refresh
                  </button>
                </div>
              </div>

              {/* Filter tabs */}
              <div className="filter-tabs">
                {[
                  { k: 'all',       label: `All (${result.total})` },
                  { k: 'triggered', label: `Triggered (${result.triggered_count})` },
                  { k: 'nosignal',  label: `No Signal (${result.results.filter(r => !r.signal && !r.error).length})` },
                  { k: 'errors',    label: `Errors (${result.results.filter(r => r.error).length})` },
                ].map(tab => (
                  <button
                    key={tab.k}
                    className={`filter-tab ${filter === tab.k ? 'active' : ''}`}
                    onClick={() => setFilter(tab.k)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Table */}
              <div className="results-wrap">
                <table className="results-table">
                  <thead>
                    <tr>
                      <th className="col-dot"/>
                      <SortTh label="Ticker"   k="ticker"   />
                      <SortTh label="Price"    k="price"    align="right"/>
                      <SortTh label="Change %" k="change_pct" align="right"/>
                      {showRSI   && <SortTh label="RSI"       k="rsi"       align="right"/>}
                      {showMACD  && <SortTh label="MACD Hist" k="macd_hist" align="right"/>}
                      {showStoch && <th className="text-right">Stoch %K</th>}
                      {showBB    && <th className="text-right">BB Lower</th>}
                      {showBB    && <th className="text-right">BB Upper</th>}
                      {showSMA   && <th className="text-right">SMA</th>}
                      {showEMA   && <th className="text-right">EMA</th>}
                      <SortTh label="Signal" k="priority" align="center"/>
                    </tr>
                  </thead>
                  <tbody>
                    {tableRows.map((item, idx) => {
                      if (item.type === 'expanded') {
                        return (
                          <tr key={`exp-${item.row.ticker}`} className="expanded-row">
                            <td colSpan={20}>
                              <div className="exp-content">
                                <span className="exp-label">All triggered rules:</span>
                                {item.row.triggered_rules.map((tr, i) => (
                                  <span key={i} className="exp-rule">
                                    <SignalBadge signal={tr.signal}/>
                                    <code>{tr.formula}</code>
                                    {tr.signal === item.row.signal && <span className="exp-winner">★ applied</span>}
                                  </span>
                                ))}
                              </div>
                            </td>
                          </tr>
                        )
                      }

                      const row = item.row
                      const isExpanded = expanded === row.ticker
                      const hasMultiple = row.triggered_rules?.length > 1

                      return (
                        <tr
                          key={`row-${row.ticker}`}
                          className={[
                            row.signal ? 'row-hit' : '',
                            isExpanded  ? 'row-open' : '',
                          ].join(' ')}
                          onClick={() => hasMultiple && setExpanded(isExpanded ? null : row.ticker)}
                          style={{ cursor: hasMultiple ? 'pointer' : 'default' }}
                        >
                          <td className="col-dot">
                            <span className={`dot ${row.signal ? 'dot-hit' : row.error ? 'dot-err' : 'dot-idle'}`}/>
                          </td>
                          <td className="col-ticker">
                            {row.ticker?.replace('.IS', '')}
                            {hasMultiple && <span className="multi-hint" title="Multiple rules triggered">+{row.triggered_rules.length}</span>}
                          </td>
                          <td className="text-right">{row.price?.toFixed(2) ?? '—'}</td>
                          <td className="text-right"><PctCell v={row.change_pct}/></td>
                          {showRSI   && <td className="text-right"><NumCell v={row.values?.RSI}       decimals={1}/></td>}
                          {showMACD  && <td className="text-right"><NumCell v={row.values?.MACD_HIST}  decimals={4}/></td>}
                          {showStoch && <td className="text-right"><NumCell v={row.values?.STOCH_K}/></td>}
                          {showBB    && <td className="text-right"><NumCell v={row.values?.BB_LOWER}/></td>}
                          {showBB    && <td className="text-right"><NumCell v={row.values?.BB_UPPER}/></td>}
                          {showSMA   && <td className="text-right"><NumCell v={row.values?.SMA}/></td>}
                          {showEMA   && <td className="text-right"><NumCell v={row.values?.EMA}/></td>}
                          <td className="text-center">
                            {row.error
                              ? <span className="signal-badge sig-error" title={row.error}>ERROR</span>
                              : <SignalBadge signal={row.signal}/>
                            }
                          </td>
                        </tr>
                      )
                    })}

                    {tableRows.length === 0 && (
                      <tr>
                        <td colSpan={20} className="empty-row">No results for current filter.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
