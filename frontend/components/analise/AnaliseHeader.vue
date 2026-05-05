<template>
  <div
    class="analise-header"
    :style="headerStyle"
  >
    <v-container class="analise-header__content">
      <h1 class="text-h3 font-weight-bold mb-2">{{ title }}</h1>
      <p v-if="description" class="text-h6 font-weight-regular text-medium-emphasis mb-4">
        {{ description }}
      </p>
      <div v-if="stats && stats.length" class="analise-header__stats d-flex flex-wrap ga-4">
        <div
          v-for="stat in stats"
          :key="stat.label"
          class="analise-header__stat"
        >
          <span class="text-h5 font-weight-bold">{{ stat.value }}</span>
          <span class="text-caption text-medium-emphasis d-block">{{ stat.label }}</span>
        </div>
      </div>
    </v-container>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  title: string
  description?: string
  stats?: Array<{ label: string; value: string | number }>
  backgroundColor?: string
  backgroundImage?: string
}>()

const headerStyle = computed(() => {
  const style: Record<string, string> = {}
  if (props.backgroundImage) {
    style.backgroundImage = `linear-gradient(rgba(255,255,255,0.85), rgba(255,255,255,0.92)), url(${props.backgroundImage})`
    style.backgroundSize = 'cover'
    style.backgroundPosition = 'center'
  } else if (props.backgroundColor) {
    style.backgroundColor = props.backgroundColor
  }
  return style
})
</script>

<style scoped>
.analise-header {
  padding: 3rem 0 2rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  margin-bottom: 2rem;
}

.analise-header__stats {
  margin-top: 1rem;
}

.analise-header__stat {
  background: rgba(0, 0, 0, 0.04);
  border-radius: 8px;
  padding: 0.75rem 1.25rem;
}

.analise-header__stat .text-h5 {
  font-family: Roboto, sans-serif !important;
}
</style>
