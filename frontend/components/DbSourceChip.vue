<script setup lang="ts">
const { data } = await useFetch('/api/db-source')

const label = computed(() => {
  switch (data.value?.source) {
    case 'vps': return 'BD completa'
    case 'turso': return 'BD lite'
    case 'local': return 'BD local'
    default: return ''
  }
})

const color = computed(() => {
  return data.value?.source === 'vps' ? 'success' : 'warning'
})

const icon = computed(() => {
  return data.value?.source === 'vps' ? 'mdi-database' : 'mdi-database-outline'
})
</script>

<template>
  <v-chip v-if="label" :color="color" size="x-small" variant="tonal" :prepend-icon="icon">
    {{ label }}
  </v-chip>
</template>
