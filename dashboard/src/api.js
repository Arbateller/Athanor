import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

export async function fetchAllStocks() {
  const { data } = await api.get('/stocks/list')
  return data
}

export async function fetchStock(ticker) {
  const { data } = await api.get(`/stock/${ticker}`)
  return data
}

export async function fetchStockHistory(ticker, period = '1mo', interval = '1d') {
  const { data } = await api.get(`/stock/${ticker}/history`, { params: { period, interval } })
  return data
}

export async function fetchHealthCheck() {
  const { data } = await api.get('/')
  return data
}

export async function fetchIndicators(ticker, indicators = [], options = {}) {
  const { data } = await api.get(`/stock/${ticker}/compute-indicators`, {
    params: {
      indicators:  indicators.join(','),
      period:      options.period     || '3mo',
      interval:    options.interval   || '1d',
      sma_period:  options.sma_period || 20,
      ema_period:  options.ema_period || 20,
    },
  })
  return data
}

/**
 * Run multi-rule scanner across all tracked stocks.
 * @param {object} params
 * @param {Array}  params.rules        [{ formula: "RSI < 30", signal: "STRONG BUY" }, ...]
 * @param {string} params.period
 * @param {number} params.sma_period
 * @param {number} params.ema_period
 */
export async function runScanner(params) {
  const { data } = await api.post('/scanner/run', params)
  return data
}
