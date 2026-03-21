import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
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
  const { data } = await api.get(`/stock/${ticker}/history`, {
    params: { period, interval },
  })
  return data
}

export async function fetchHealthCheck() {
  const { data } = await api.get('/')
  return data
}
