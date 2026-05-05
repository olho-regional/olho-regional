<template>
  <div class="gender-keywords">
    <div class="gender-keywords__chips d-flex flex-wrap ga-2 mb-4">
      <v-chip
        v-for="kw in keywords"
        :key="kw"
        :color="selected === kw ? 'grey-darken-3' : undefined"
        :variant="selected === kw ? 'flat' : 'outlined'"
        @click="selected = kw"
      >
        {{ kw }}
      </v-chip>
    </div>
    <ClientOnly>
      <VChart
        v-if="chartOption"
        :option="chartOption"
        autoresize
        style="min-height: 300px; width: 100%"
      />
    </ClientOnly>
    <p v-if="caption" class="text-caption text-medium-emphasis mt-2 text-center">
      {{ caption }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  /** Pre-compiled data keyed by keyword: { [keyword]: { year, M, F }[] } */
  data: Record<string, { year: string; M: number; F: number }[]>
  keywords: string[]
  caption?: string
}>()

const selected = ref(props.keywords[0] || '')

const chartOption = computed(() => {
  const rows = props.data[selected.value]
  if (!rows?.length) return null

  const years = rows.map(d => d.year)
  const maleData = rows.map(d => d.M)
  const femaleData = rows.map(d => d.F)
  const malePct = maleData.map((m, i) => {
    const t = m + (femaleData[i] || 0)
    return t ? Math.round((m / t) * 1000) / 10 : 0
  })
  const femalePct = femaleData.map((f, i) => {
    const t = (maleData[i] || 0) + f
    return t ? Math.round((f / t) * 1000) / 10 : 0
  })

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        const year = params[0]?.axisValue || ''
        const idx = years.indexOf(year)
        const m = maleData[idx] || 0
        const f = femaleData[idx] || 0
        return params.map((p: any) =>
          `<span style="color:${p.color}">●</span> ${p.seriesName}: ${p.value}% (${(p.seriesName === 'Masculino' ? m : f).toLocaleString()})`
        ).join('<br>') + `<br><span style="color:#999">Total: ${(m + f).toLocaleString()}</span>`
      },
    },
    legend: { data: ['Masculino', 'Feminino'], bottom: 0 },
    xAxis: { type: 'category', data: years, boundaryGap: false },
    yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    series: [
      { name: 'Masculino', type: 'line', stack: 'gender', data: malePct, areaStyle: { opacity: 0.85 }, lineStyle: { width: 0 }, itemStyle: { color: '#1565c0' }, symbol: 'none', smooth: true },
      { name: 'Feminino', type: 'line', stack: 'gender', data: femalePct, areaStyle: { opacity: 0.85 }, lineStyle: { width: 0 }, itemStyle: { color: '#E65100' }, symbol: 'none', smooth: true },
    ],
    grid: { left: 48, right: 20, top: 16, bottom: 40 },
  }
})
</script>
