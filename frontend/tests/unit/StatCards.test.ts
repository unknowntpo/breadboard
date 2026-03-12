import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import StatCards from '../../src/components/StatCards.vue'

const RECORD = { date: '2024-01-03', symbol: 'AAPL', open: 185.0, high: 190.5, low: 183.25, close: 189.0, volume: 1000000 }

describe('StatCards', () => {
  it('shows dashes when records is empty', () => {
    const wrapper = mount(StatCards, { props: { records: [] } })
    const values = wrapper.findAll('.text-2xl')
    expect(values.every(v => v.text() === '—')).toBe(true)
  })

  it('shows latest record values formatted to 2 decimals', () => {
    const wrapper = mount(StatCards, { props: { records: [RECORD] } })
    const values = wrapper.findAll('.text-2xl').map(v => v.text())
    expect(values).toContain('$185.00')
    expect(values).toContain('$190.50')
    expect(values).toContain('$183.25')
    expect(values).toContain('$189.00')
  })

  it('uses last record when multiple records provided', () => {
    const older = { ...RECORD, date: '2024-01-02', close: 100.0 }
    const wrapper = mount(StatCards, { props: { records: [older, RECORD] } })
    const values = wrapper.findAll('.text-2xl').map(v => v.text())
    expect(values).toContain('$189.00') // from RECORD (latest)
  })
})
