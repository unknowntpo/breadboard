import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
  },
}))

import axios from 'axios'
import { fetchHistory } from '../../src/api/history'

describe('fetchHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls GET /api/v1/history with correct params', async () => {
    const mockData = { records: [], count: 0, symbol: 'AAPL' }
    ;(axios.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: mockData })

    const result = await fetchHistory('AAPL', '2024-01-01', '2024-12-31')

    expect(axios.get).toHaveBeenCalledWith('/api/v1/history', {
      params: { symbol: 'AAPL', start: '2024-01-01', end: '2024-12-31' },
    })
    expect(result).toEqual(mockData)
  })

  it('propagates axios errors', async () => {
    ;(axios.get as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network Error'))
    await expect(fetchHistory('AAPL', '2024-01-01', '2024-12-31')).rejects.toThrow('Network Error')
  })
})
