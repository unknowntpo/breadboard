import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import OhlcvTable from '../../src/components/OhlcvTable.vue'

const RECORDS = [
  { date: '2024-01-02', symbol: 'AAPL', open: 185.0, high: 188.0, low: 184.0, close: 187.0, volume: 1000000 },
  { date: '2024-01-03', symbol: 'AAPL', open: 187.0, high: 190.0, low: 186.0, close: 189.0, volume: 1200000 },
]

describe('OhlcvTable', () => {
  it('shows "No data" when records is empty', () => {
    const wrapper = mount(OhlcvTable, { props: { records: [] } })
    expect(wrapper.text()).toContain('No data')
  })

  it('renders column headers', () => {
    const wrapper = mount(OhlcvTable, { props: { records: RECORDS } })
    const headers = wrapper.findAll('th').map(h => h.text())
    expect(headers).toEqual(['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
  })

  it('renders rows sorted descending by date', () => {
    const wrapper = mount(OhlcvTable, { props: { records: RECORDS } })
    const rows = wrapper.findAll('tbody tr')
    expect(rows[0].text()).toContain('2024-01-03')
    expect(rows[1].text()).toContain('2024-01-02')
  })

  it('high cell has green text class', () => {
    const wrapper = mount(OhlcvTable, { props: { records: [RECORDS[0]] } })
    const cells = wrapper.findAll('tbody td')
    // cells: date, open, high, low, close, volume
    expect(cells[2].classes()).toContain('text-[#22C55E]')
    expect(cells[3].classes()).toContain('text-[#EF4444]')
  })
})
