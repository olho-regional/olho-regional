<template>
  <div class="analise-map-comparison">
    <!-- Time controls -->
    <div v-if="animated && years.length > 1" class="d-flex align-center justify-center mb-4 ga-3">
      <v-btn
        :icon="playing ? 'mdi-stop' : 'mdi-play'"
        size="small"
        variant="tonal"
        @click="togglePlay"
      />
      <v-slider
        v-model="currentYearIndex"
        :min="0"
        :max="years.length"
        :step="1"
        hide-details
        style="max-width: 300px"
        color="primary"
      />
      <span class="text-body-2 font-weight-bold" style="min-width: 50px">{{ currentYear }}</span>
    </div>

    <!-- Side-by-side maps -->
    <v-row>
      <v-col
        v-for="(s, i) in seriesData"
        :key="i"
        cols="12"
        :md="12 / seriesData.length"
      >
        <p class="text-subtitle-2 text-center mb-2">{{ s.label }}</p>
        <ClientOnly>
          <PortugalMap
            :district-counts="getCountsForSeries(i)"
            :count-label="props.countLabel ?? 'citações'"
            :max-override="sharedMax"
            :hue="props.hues?.[i] ?? 210"
            :geojson-url="props.geojsonUrl"
            :label-field="props.labelField"
          />
        </ClientOnly>
      </v-col>
    </v-row>

    <p v-if="caption" class="text-caption text-medium-emphasis mt-2 text-center">
      {{ caption }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount } from 'vue'

interface SeriesData {
  label: string
  years: string[]
  districts: Record<string, Record<string, number>>
}

const props = defineProps<{
  seriesData: SeriesData[]
  animated?: boolean
  caption?: string
  hues?: number[]
  geojsonUrl?: string
  labelField?: string
  countLabel?: string
}>()

const years = computed(() => {
  if (!props.seriesData.length) return []
  return props.seriesData[0].years
})

// Slider goes from 0 to years.length (inclusive) — last position = "Total"
const currentYearIndex = ref(years.value.length)
const playing = ref(false)
let playInterval: ReturnType<typeof setInterval> | null = null

const isTotal = computed(() => currentYearIndex.value >= years.value.length)
const currentYear = computed(() => isTotal.value ? 'Total' : (years.value[currentYearIndex.value] || ''))

/** Get district counts for a series at the current year (or total if at end) */
function getCountsForSeries(seriesIndex: number): Record<string, number> {
  const s = props.seriesData[seriesIndex]
  if (!s) return {}

  if (props.animated && years.value.length > 1 && !isTotal.value) {
    const year = years.value[currentYearIndex.value]
    const result: Record<string, number> = {}
    for (const [district, yearCounts] of Object.entries(s.districts)) {
      result[district] = yearCounts[year] || 0
    }
    return result
  }

  // Not animated or "Total": sum all years
  const result: Record<string, number> = {}
  for (const [district, yearCounts] of Object.entries(s.districts)) {
    result[district] = Object.values(yearCounts).reduce((a, b) => a + b, 0)
  }
  return result
}

/** Shared max across both maps so colors are comparable */
const sharedMax = computed(() => {
  let max = 1
  for (let i = 0; i < props.seriesData.length; i++) {
    const counts = getCountsForSeries(i)
    for (const v of Object.values(counts)) {
      if (v > max) max = v
    }
  }
  return max
})

function togglePlay() {
  if (playing.value) {
    stopPlay()
  } else {
    startPlay()
  }
}

function startPlay() {
  playing.value = true
  currentYearIndex.value = 0
  playInterval = setInterval(() => {
    if (currentYearIndex.value >= years.value.length) {
      stopPlay()
    } else {
      currentYearIndex.value++
    }
  }, 250)
}

function stopPlay() {
  playing.value = false
  if (playInterval) {
    clearInterval(playInterval)
    playInterval = null
  }
}

onBeforeUnmount(() => {
  stopPlay()
})
</script>
