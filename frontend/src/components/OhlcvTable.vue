<template>
  <div class="bg-white border border-[#E6E6E6] rounded-lg overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-[#E6E6E6] bg-[#FAFAFA]">
            <th v-for="col in cols" :key="col" class="px-4 py-3 text-left text-xs font-semibold text-[#666666] uppercase tracking-wide">
              {{ col }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, i) in sorted"
            :key="i"
            class="border-b border-[#E6E6E6] last:border-0 hover:bg-[#FAFAFA]"
          >
            <td class="px-4 py-2 font-mono text-[#0D0D0D]">{{ row.date }}</td>
            <td class="px-4 py-2 font-mono">{{ row.open.toFixed(2) }}</td>
            <td class="px-4 py-2 font-mono text-[#22C55E]">{{ row.high.toFixed(2) }}</td>
            <td class="px-4 py-2 font-mono text-[#EF4444]">{{ row.low.toFixed(2) }}</td>
            <td class="px-4 py-2 font-mono font-semibold">{{ row.close.toFixed(2) }}</td>
            <td class="px-4 py-2 font-mono text-[#666666]">{{ row.volume.toLocaleString() }}</td>
          </tr>
          <tr v-if="!sorted.length">
            <td colspan="6" class="px-4 py-8 text-center text-[#666666]">No data</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { HistoryRecord } from '@/api/history'

const props = defineProps<{ records: HistoryRecord[] }>()

const cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']

const sorted = computed(() =>
  [...props.records].sort((a, b) => b.date.localeCompare(a.date))
)
</script>
