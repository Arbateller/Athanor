import { useState, useEffect } from 'react'
import { ArrowLeft, TrendingUp, TrendingDown, Activity, Clock } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, AreaChart, Area, BarChart, Bar } from 'recharts'
import { fetchStock, fetchStockHistory } from '../api'
import './StockDetail.css'

const PERIODS = [
  { value: '5d', label: '5D' },
  { value: '1mo', label: '1M' },
  { value: '3mo', label: '3M' },
  { value: '6mo', label: '6M' },
  { value: '1y', label: '1Y' },
]

function formatNumber(n) {
  if (n == null) return '-'
  if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B'
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return n.toLocaleString()
}

const SIGNAL_CLASS = {
  'STRONG BUY': 'signal-strong-buy',
  'BUY': 'signal-buy',
  'HOLD': 'signal-hold',
  'SELL': 'signal-sell',
  'STRONG SELL': 'signal-strong-sell',
}

export function StockDetail({ ticker, onBack }) {
  const [stock, setStock] = useState(null)
  const [history, setHistory] = useState(null)
  const [period, setPeriod] = useState('1mo')
  const [loading, setLoading] = useState(true)
  const [histLoading, setHistLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchStock(ticker).then(data => {
      setStock(data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [ticker])

  useEffect(() => {
    setHistLoading(true)
    const interval = period === '5d' ? '15m' : period === '1mo' ? '1d' : '1d'
    fetchStockHistory(ticker, period, interval).then(data => {
      setHistory(data)
      setHistLoading(false)
    }).catch(() => setHistLoading(false))
  }, [ticker, period])

  if (loading) {
    return (
      <div className="detail-page">
        <button className="back-btn" onClick={onBack}><ArrowLeft size={16} /> Back</button>
        <div className="loading-skeleton" style={{ height: 200, marginTop: 16 }} />
      </div>
    )
  }

  if (!stock) {
    return (
      <div className="detail-page">
        <button className="back-btn" onClick={onBack}><ArrowLeft size={16} /> Back</button>
        <div className="detail-empty">Stock data not available. Make sure the fetcher is running.</div>
      </div>
    )
  }

  const isPositive = (stock.change_pct ?? stock.change ?? 0) >= 0
  const changePct = stock.change_pct ?? 0
  const change = stock.change ?? 0
  const indicators = stock.indicators || {}
  const rsi = indicators.rsi_14
  const macdLine = indicators.macd_line
  const macdSignal = indicators.macd_signal
  const macdHist = indicators.macd_hist

  const chartData = history?.data?.map(d => ({
    ...d,
    date: d.date?.length > 10 ? new Date(d.date).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : d.date,
  })) || []

  const chartColor = chartData.length >= 2 && chartData[chartData.length - 1].close >= chartData[0].close ? '#10b981' : '#ef4444'

  return (
    <div className="detail-page">
      <button className="back-btn" onClick={onBack}><ArrowLeft size={16} /> Back to list</button>

      <div className="detail-header">
        <div className="detail-title-row">
          <h1>{ticker.replace('.IS', '')}</h1>
          <span className={`signal-badge ${SIGNAL_CLASS[stock.signal] || ''}`}>{stock.signal || 'N/A'}</span>
        </div>
        {stock.signal_reason && <p className="signal-reason">{stock.signal_reason}</p>}
        <div className="detail-price-row">
          <span className="detail-price">{stock.price?.toFixed(2) ?? '-'}</span>
          <span className="detail-currency">{stock.currency || 'TRY'}</span>
          <span className={`detail-change ${isPositive ? 'positive' : 'negative'}`}>
            {isPositive ? '+' : ''}{change.toFixed(2)} ({isPositive ? '+' : ''}{changePct.toFixed(2)}%)
          </span>
        </div>
      </div>

      <div className="detail-chart-card">
        <div className="chart-period-tabs">
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
        {histLoading ? (
          <div className="loading-skeleton" style={{ height: 300 }} />
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={chartColor} stopOpacity={0.2} />
                  <stop offset="95%" stopColor={chartColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2e303a" />
              <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
              <YAxis domain={['auto', 'auto']} tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: '#1e1f2b', border: '1px solid #2e303a', borderRadius: '8px', fontSize: '13px' }}
                itemStyle={{ color: '#e4e5e9' }}
                labelStyle={{ color: '#9ca3af' }}
              />
              <Area type="monotone" dataKey="close" stroke={chartColor} strokeWidth={2} fill="url(#colorClose)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {chartData.length > 0 && (
        <div className="detail-chart-card" style={{ marginTop: 16 }}>
          <h3>Volume</h3>
          <ResponsiveContainer width="100%" height={120}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2e303a" />
              <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={formatNumber} />
              <Tooltip
                contentStyle={{ background: '#1e1f2b', border: '1px solid #2e303a', borderRadius: '8px', fontSize: '13px' }}
                itemStyle={{ color: '#e4e5e9' }}
                formatter={v => formatNumber(v)}
              />
              <Bar dataKey="volume" fill="#6366f140" stroke="#6366f1" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="detail-grid">
        <div className="detail-info-card">
          <h3>Price Details</h3>
          <div className="info-list">
            <InfoRow label="Open" value={stock.open?.toFixed(2)} />
            <InfoRow label="High" value={stock.high?.toFixed(2)} />
            <InfoRow label="Low" value={stock.low?.toFixed(2)} />
            <InfoRow label="Prev Close" value={stock.prev_close?.toFixed(2)} />
            <InfoRow label="Volume" value={formatNumber(stock.volume)} />
            <InfoRow label="Market Cap" value={formatNumber(stock.market_cap)} />
          </div>
        </div>

        <div className="detail-info-card">
          <h3>52-Week Range</h3>
          <div className="range-bar-container">
            <div className="range-labels">
              <span>{stock['52w_low']?.toFixed(2) ?? '-'}</span>
              <span>{stock['52w_high']?.toFixed(2) ?? '-'}</span>
            </div>
            {stock['52w_low'] != null && stock['52w_high'] != null && stock.price != null && (
              <div className="range-bar">
                <div
                  className="range-fill"
                  style={{
                    width: `${Math.min(100, Math.max(0, ((stock.price - stock['52w_low']) / (stock['52w_high'] - stock['52w_low'])) * 100))}%`
                  }}
                />
                <div
                  className="range-marker"
                  style={{
                    left: `${Math.min(100, Math.max(0, ((stock.price - stock['52w_low']) / (stock['52w_high'] - stock['52w_low'])) * 100))}%`
                  }}
                />
              </div>
            )}
          </div>
          <div className="info-list" style={{ marginTop: 16 }}>
            <InfoRow label="Exchange" value={stock.exchange} />
            <InfoRow label="Currency" value={stock.currency} />
            {stock.fetched_at && <InfoRow label="Last Fetched" value={new Date(stock.fetched_at).toLocaleString()} />}
          </div>
        </div>

        <div className="detail-info-card">
          <h3>Technical Indicators</h3>
          <div className="info-list">
            <InfoRow label="RSI (14)" value={rsi?.toFixed(2) ?? '-'} />
            <InfoRow label="MACD Line" value={macdLine?.toFixed(4) ?? '-'} />
            <InfoRow label="MACD Signal" value={macdSignal?.toFixed(4) ?? '-'} />
            <InfoRow label="MACD Histogram" value={macdHist?.toFixed(4) ?? '-'} />
          </div>

          {rsi != null && (
            <div className="rsi-gauge">
              <div className="rsi-bar">
                <div className="rsi-zone rsi-oversold" />
                <div className="rsi-zone rsi-neutral" />
                <div className="rsi-zone rsi-overbought" />
                <div className="rsi-needle" style={{ left: `${Math.min(100, Math.max(0, rsi))}%` }} />
              </div>
              <div className="rsi-labels">
                <span>Oversold</span>
                <span>Neutral</span>
                <span>Overbought</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function InfoRow({ label, value }) {
  return (
    <div className="info-row">
      <span className="info-label">{label}</span>
      <span className="info-value">{value ?? '-'}</span>
    </div>
  )
}
