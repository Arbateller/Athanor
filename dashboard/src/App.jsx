import { useState, useEffect, useCallback } from 'react'
import { Sidebar } from './components/Sidebar'
import { Dashboard } from './components/Dashboard'
import { StockTable } from './components/StockTable'
import { StockDetail } from './components/StockDetail'
import { IndicatorPanel } from './components/IndicatorPanel'
import { fetchAllStocks } from './api'
import './App.css'

const REFRESH_INTERVAL = 30_000

function App() {
  const [stocks,        setStocks]        = useState([])
  const [loading,       setLoading]       = useState(true)
  const [error,         setError]         = useState(null)
  const [selectedStock, setSelectedStock] = useState(null)
  const [view,          setView]          = useState('dashboard')
  const [lastUpdated,   setLastUpdated]   = useState(null)
  const [searchQuery,   setSearchQuery]   = useState('')

  const loadStocks = useCallback(async () => {
    try {
      const data = await fetchAllStocks()
      setStocks(data)
      setLastUpdated(new Date())
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStocks()
    const interval = setInterval(loadStocks, REFRESH_INTERVAL)
    return () => clearInterval(interval)
  }, [loadStocks])

  const handleSelectStock = (stock) => {
    setSelectedStock(stock)
    setView('detail')
  }

  const filteredStocks = stocks.filter(s =>
    s.Ticker?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.Name?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="app">
      <Sidebar
        view={view}
        onViewChange={(v) => { setView(v); if (v !== 'detail') setSelectedStock(null) }}
        lastUpdated={lastUpdated}
        stockCount={stocks.length}
        onRefresh={loadStocks}
      />
      <main className="main-content">
        {error && (
          <div className="error-banner">
            <span>Unable to connect to API: {error}</span>
            <button onClick={loadStocks}>Retry</button>
          </div>
        )}

        {view === 'dashboard' && (
          <Dashboard stocks={stocks} loading={loading} onSelectStock={handleSelectStock} />
        )}

        {view === 'stocks' && (
          <StockTable
            stocks={filteredStocks}
            loading={loading}
            onSelectStock={handleSelectStock}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
          />
        )}

        {view === 'detail' && selectedStock && (
          <StockDetail
            ticker={selectedStock.Ticker}
            onBack={() => setView('stocks')}
          />
        )}

        {view === 'signals' && (
          <StockTable
            stocks={filteredStocks.filter(s => s.Signal && s.Signal !== 'HOLD')}
            loading={loading}
            onSelectStock={handleSelectStock}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            title="Active Signals"
          />
        )}

        {view === 'indicators' && (
          <IndicatorPanel stocks={stocks} />
        )}
      </main>
    </div>
  )
}

export default App
