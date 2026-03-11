<template>
  <div class="flex gap-2">
    <button
      v-for="s in symbols"
      :key="s"
      @click="$emit('update:modelValue', s)"
      :class="[
        'px-4 py-1.5 rounded-full text-sm font-semibold border transition-colors',
        modelValue === s
          ? 'bg-[#FF6900] text-white border-[#FF6900]'
          : 'bg-white text-[#0D0D0D] border-[#E6E6E6] hover:border-[#FF6900] hover:text-[#FF6900]'
      ]"
    >
      {{ s }}
    </button>
  </div>
</template>

<script setup>
defineProps({ modelValue: String })
defineEmits(['update:modelValue'])
const symbols = ['AAPL', 'TSLA']
</script>
