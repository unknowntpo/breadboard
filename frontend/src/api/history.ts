import axios from 'axios'

export interface HistoryRecord {
  date: string
  symbol: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export async function fetchHistory(
  symbol: string,
  start: string,
  end: string
): Promise<{ records: HistoryRecord[] }> {
  const res = await axios.get('/api/v1/history', { params: { symbol, start, end } })
  return res.data
}
