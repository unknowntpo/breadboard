<template>
  <div class="bg-white border border-[#E6E6E6] rounded-lg p-4">
    <div ref="chartContainer" style="height: 320px;"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { createChart, CandlestickSeries, type IChartApi, type ISeriesApi } from 'lightweight-charts'
import type { HistoryRecord } from '@/api/history'

const props = defineProps<{ records: HistoryRecord[] }>()

const chartContainer = ref<HTMLDivElement | null>(null)
let chart: IChartApi | null = null
let series: ISeriesApi<'Candlestick'> | null = null

function initChart() {
  if (!chartContainer.value) return
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

  series = chart.addSeries(CandlestickSeries, {
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
      time: r.date as `${number}-${number}-${number}`,
      open: r.open,
      high: r.high,
      low: r.low,
      close: r.close,
    }))
    .sort((a, b) => a.time.localeCompare(b.time))
  series.setData(data)
  chart?.timeScale().fitContent()
}

onMounted(() => {
  initChart()
  updateData()

  if (!chartContainer.value) return
  const ro = new ResizeObserver(() => {
    if (chart && chartContainer.value) {
      chart.applyOptions({ width: chartContainer.value.clientWidth })
    }
  })
  ro.observe(chartContainer.value)
})

onBeforeUnmount(() => {
  chart?.remove()
})

watch(() => props.records, updateData, { deep: true })
</script>
