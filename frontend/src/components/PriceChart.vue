<template>
  <div class="bg-white border border-[#E6E6E6] rounded-lg p-4">
    <div ref="chartContainer" style="height: 320px;"></div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { createChart } from 'lightweight-charts'

const props = defineProps({
  records: { type: Array, default: () => [] }
})

const chartContainer = ref(null)
let chart = null
let series = null

function initChart() {
  chart = createChart(chartContainer.value, {
    layout: {
      background: { color: '#FFFFFF' },
      textColor: '#0D0D0D',
    },
    grid: {
      vertLines: { color: '#E6E6E6' },
      horzLines: { color: '#E6E6E6' },
    },
    rightPriceScale: { borderColor: '#E6E6E6' },
    timeScale: { borderColor: '#E6E6E6', timeVisible: true },
    width: chartContainer.value.clientWidth,
    height: 320,
  })

  series = chart.addCandlestickSeries({
    upColor: '#22C55E',
    downColor: '#EF4444',
    borderUpColor: '#22C55E',
    borderDownColor: '#EF4444',
    wickUpColor: '#22C55E',
    wickDownColor: '#EF4444',
  })
}

function updateData() {
  if (!series || !props.records.length) return
  const data = props.records
    .map(r => ({
      time: r.date,
      open: r.open,
      high: r.high,
      low: r.low,
      close: r.close,
    }))
    .sort((a, b) => a.time.localeCompare(b.time))
  series.setData(data)
  chart.timeScale().fitContent()
}

onMounted(() => {
  initChart()
  updateData()

  const ro = new ResizeObserver(() => {
    chart.applyOptions({ width: chartContainer.value.clientWidth })
  })
  ro.observe(chartContainer.value)
})

onBeforeUnmount(() => {
  chart?.remove()
})

watch(() => props.records, updateData, { deep: true })
</script>
