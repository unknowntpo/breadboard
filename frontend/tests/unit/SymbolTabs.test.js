import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import SymbolTabs from '../../src/components/SymbolTabs.vue'

describe('SymbolTabs', () => {
  it('renders AAPL and TSLA buttons', () => {
    const wrapper = mount(SymbolTabs, { props: { modelValue: 'AAPL' } })
    const buttons = wrapper.findAll('button')
    expect(buttons).toHaveLength(2)
    expect(buttons[0].text()).toBe('AAPL')
    expect(buttons[1].text()).toBe('TSLA')
  })

  it('active button has orange background class', () => {
    const wrapper = mount(SymbolTabs, { props: { modelValue: 'TSLA' } })
    const buttons = wrapper.findAll('button')
    expect(buttons[1].classes()).toContain('bg-[#FF6900]')
    expect(buttons[0].classes()).not.toContain('bg-[#FF6900]')
  })

  it('emits update:modelValue on click', async () => {
    const wrapper = mount(SymbolTabs, { props: { modelValue: 'AAPL' } })
    await wrapper.findAll('button')[1].trigger('click')
    expect(wrapper.emitted('update:modelValue')).toEqual([['TSLA']])
  })
})
