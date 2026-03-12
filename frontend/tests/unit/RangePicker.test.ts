import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import RangePicker from '../../src/components/RangePicker.vue'

describe('RangePicker', () => {
  it('renders 5 range buttons', () => {
    const wrapper = mount(RangePicker, { props: { modelValue: '1M' } })
    const buttons = wrapper.findAll('button')
    expect(buttons).toHaveLength(5)
    expect(buttons.map(b => b.text())).toEqual(['1W', '1M', '3M', '1Y', 'All'])
  })

  it('active button has orange background', () => {
    const wrapper = mount(RangePicker, { props: { modelValue: '3M' } })
    const buttons = wrapper.findAll('button')
    expect(buttons[2].classes()).toContain('bg-[#FF6900]')
    expect(buttons[0].classes()).not.toContain('bg-[#FF6900]')
  })

  it('emits update:modelValue with clicked label', async () => {
    const wrapper = mount(RangePicker, { props: { modelValue: '1M' } })
    await wrapper.findAll('button')[3].trigger('click') // 1Y
    expect(wrapper.emitted('update:modelValue')).toEqual([['1Y']])
  })
})
