import { useState, useMemo } from 'react'
import { Search, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import './StockTable.css'

function formatNumber(n) {
  if (n == null) return '-'
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B'
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
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

const COLUMNS = [
  { key: 'Ticker', label: 'Ticker', format: v => v?.replace('.IS', '') },
  { key: 'Price', label: 'Price', align: 'right', format: v => v?.toFixed(2) ?? '-' },
  { key: 'Change %', label: 'Change %', align: 'right', format: v => v != null ? (v >= 0 ? '+' : '') + v.toFixed(2) + '%' : '-' },
  { key: 'Volume', label: 'Volume', align: 'right', format: formatNumber },
  { key: 'Market Cap', label: 'Mkt Cap', align: 'right', format: formatNumber },
  { key: 'RSI 14', label: 'RSI', align: 'right', format: v => v?.toFixed(1) ?? '-' },
  { key: 'MACD Hist', label: 'MACD', align: 'right', format: v => v?.toFixed(4) ?? '-' },
  { key: 'Signal', label: 'Signal', align: 'center' },
]

export function StockTable({ stocks, loading, onSelectStock, searchQuery, onSearchChange, title }) {
  const [sortKey, setSortKey] = useState('Ticker')
  const [sortDir, setSortDir] = useState('asc')

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir(key === 'Ticker' ? 'asc' : 'desc')
    }
  }

  const sorted = useMemo(() => {
    return [...stocks].sort((a, b) => {
      let av = a[sortKey], bv = b[sortKey]
      if (av == null) return 1
      if (bv == null) return -1
      if (typeof av === 'string') {
        const cmp = av.localeCompare(bv)
        return sortDir === 'asc' ? cmp : -cmp
      }
      return sortDir === 'asc' ? av - bv : bv - av
    })
  }, [stocks, sortKey, sortDir])

  return (
    <div className="stock-table-page">
      <div className="page-header">
        <h1>{title || 'All Stocks'}</h1>
        <p>{stocks.length} stocks</p>
      </div>

      <div className="table-toolbar">
        <div className="search-box">
          <Search size={16} />
          <input
            type="text"
            placeholder="Search by ticker or name..."
            value={searchQuery}
            onChange={e => onSearchChange(e.target.value)}
          />
        </div>
      </div>

      {loading ? (
        <div className="table-loading">
          {[...Array(10)].map((_, i) => (
            <div key={i} className="loading-skeleton" style={{ height: 44, marginBottom: 2 }} />
          ))}
        </div>
      ) : (
        <div className="table-wrapper">
          <table className="stock-table">
            <thead>
              <tr>
                {COLUMNS.map(col => (
                  <th
                    key={col.key}
                    className={col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : ''}
                    onClick={() => handleSort(col.key)}
                  >
                    <div className="th-content">
                      <span>{col.label}</span>
                      {sortKey === col.key ? (
                        sortDir === 'asc' ? <ArrowUp size={13} /> : <ArrowDown size={13} />
                      ) : (
                        <ArrowUpDown size={13} className="sort-idle" />
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map(stock => (
                <tr key={stock.Ticker} onClick={() => onSelectStock(stock)}>
                  {COLUMNS.map(col => {
                    const val = stock[col.key]
                    if (col.key === 'Signal') {
                      return (
                        <td key={col.key} className="text-center">
                          <span className={`signal-badge ${SIGNAL_CLASS[val] || ''}`}>
                            {val || '-'}
                          </span>
                        </td>
                      )
                    }
                    if (col.key === 'Change %') {
                      const cls = val > 0 ? 'positive' : val < 0 ? 'negative' : ''
                      return (
                        <td key={col.key} className={`text-right ${cls}`}>
                          {col.format(val)}
                        </td>
                      )
                    }
                    return (
                      <td key={col.key} className={col.align === 'right' ? 'text-right' : ''}>
                        {col.format ? col.format(val) : val}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
