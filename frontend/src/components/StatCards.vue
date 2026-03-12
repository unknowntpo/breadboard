<template>
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
    <div
      v-for="card in cards"
      :key="card.label"
      class="bg-white border border-[#E6E6E6] rounded-lg p-4"
    >
      <div class="text-xs text-[#666666] font-medium uppercase tracking-wide mb-1">{{ card.label }}</div>
      <div class="text-2xl font-bold text-[#0D0D0D]">
        {{ card.value !== null ? `$${card.value.toFixed(2)}` : '—' }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { HistoryRecord } from '@/api/history'

const props = defineProps<{ records: HistoryRecord[] }>()

const latest = computed(() => props.records.length ? props.records[props.records.length - 1] : null)

const cards = computed(() => [
  { label: 'Open',  value: latest.value?.open  ?? null },
  { label: 'High',  value: latest.value?.high  ?? null },
  { label: 'Low',   value: latest.value?.low   ?? null },
  { label: 'Close', value: latest.value?.close ?? null },
])
</script>
