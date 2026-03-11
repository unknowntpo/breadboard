<template>
  <div class="flex gap-2">
    <button
      v-for="r in ranges"
      :key="r.label"
      @click="$emit('update:modelValue', r.label)"
      :class="[
        'px-3 py-1 rounded text-sm font-medium border transition-colors',
        modelValue === r.label
          ? 'bg-[#FF6900] text-white border-[#FF6900]'
          : 'bg-white text-[#666666] border-[#E6E6E6] hover:border-[#FF6900] hover:text-[#FF6900]'
      ]"
    >
      {{ r.label }}
    </button>
  </div>
</template>

<script setup>
defineProps({ modelValue: String })
defineEmits(['update:modelValue'])

const ranges = [
  { label: '1W' },
  { label: '1M' },
  { label: '3M' },
  { label: '1Y' },
  { label: 'All' },
]
</script>
