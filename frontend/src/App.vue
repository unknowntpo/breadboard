<template>
  <div class="min-h-screen bg-[#FAFAFA]">
    <!-- Nav -->
    <nav class="bg-white border-b border-[#E6E6E6] px-6 py-4 flex items-center gap-4">
      <span class="text-[#FF6900] font-bold text-lg tracking-tight">breadboard</span>
      <span class="text-[#E6E6E6]">|</span>
      <span class="text-[#666666] text-sm">Historical Data</span>
    </nav>

    <main class="max-w-6xl mx-auto px-6 py-8 space-y-6">
      <!-- Controls -->
      <div class="flex flex-wrap items-center gap-4">
        <SymbolTabs v-model="symbol" />
        <div class="flex-1"></div>
        <RangePicker v-model="range" />
      </div>

      <!-- Error -->
      <div v-if="error" class="bg-red-50 border border-[#EF4444] text-[#EF4444] px-4 py-3 rounded-lg text-sm">
        {{ error }}
      </div>

      <!-- Loading -->
      <div v-if="loading" class="text-center py-16 text-[#666666]">Loading...</div>

      <template v-else>
        <StatCards :records="records" />
        <PriceChart :records="records" />
        <OhlcvTable :records="records" />
      </template>
    </main>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import SymbolTabs from './components/SymbolTabs.vue'
import RangePicker from './components/RangePicker.vue'
import StatCards from './components/StatCards.vue'
import PriceChart from './components/PriceChart.vue'
import OhlcvTable from './components/OhlcvTable.vue'
import { fetchHistory } from './api/history.js'

const symbol = ref('AAPL')
const range = ref('1M')
const records = ref([])
const loading = ref(false)
const error = ref(null)

function dateRange(r) {
  const end = new Date()
  const start = new Date()
  const map = { '1W': 7, '1M': 30, '3M': 90, '1Y': 365, 'All': 3650 }
  start.setDate(end.getDate() - (map[r] ?? 30))
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  }
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const { start, end } = dateRange(range.value)
    const data = await fetchHistory(symbol.value, start, end)
    records.value = data.records ?? []
  } catch (e) {
    error.value = e?.response?.data?.detail ?? e.message
    records.value = []
  } finally {
    loading.value = false
  }
}

watch([symbol, range], load)
onMounted(load)
</script>
