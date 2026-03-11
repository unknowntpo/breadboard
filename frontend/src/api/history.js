import axios from 'axios'

export async function fetchHistory(symbol, start, end) {
  const { data } = await axios.get('/api/v1/history', {
    params: { symbol, start, end }
  })
  return data
}
