<template>
  <div class="analise-viz">
    <ClientOnly>
      <AnaliseMapComparison
        v-if="viz.type === 'map-comparison' && viz.data"
        :series-data="viz.data.series"
        :animated="viz.data.animated"
        :caption="viz.caption"
        :hues="viz.data.hues"
        :geojson-url="viz.data.geojsonUrl"
        :label-field="viz.data.labelField"
        :count-label="viz.data.countLabel"
      />
      <AnaliseGenderKeywords
        v-else-if="viz.type === 'gender-keywords' && viz.data"
        :data="viz.data.results"
        :keywords="viz.data.keywords"
        :caption="viz.caption"
      />
      <VChart
        v-else-if="chartOption"
        :option="chartOption"
        autoresize
        style="min-height: 300px; width: 100%"
      />
      <PortugalMap
        v-else-if="viz.type === 'map' && mapCounts"
        :district-counts="mapCounts"
        count-label="artigos"
      />
      <div v-else class="d-flex align-center justify-center pa-8 bg-grey-lighten-4 rounded">
        <v-icon size="32" class="mr-2">mdi-chart-box-outline</v-icon>
        <span class="text-body-2 text-medium-emphasis">{{ viz.type }}</span>
      </div>
    </ClientOnly>
    <p v-if="viz.caption && viz.type !== 'map-comparison' && viz.type !== 'gender-keywords'" class="text-caption text-medium-emphasis mt-2 text-center">
      {{ viz.caption }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { VizCompiled } from '~/types/analise'

const props = defineProps<{
  viz: VizCompiled
}>()

/** For map: convert {name, count}[] to Record<name, count> */
const mapCounts = computed(() => {
  if (props.viz.type !== 'map' || !props.viz.data) return null
  const map: Record<string, number> = {}
  for (const d of props.viz.data) map[d.name] = d.count
  return map
})

const chartOption = computed(() => {
  const data = props.viz.data
  if (!data || props.viz.type === 'map') return null

  switch (props.viz.type) {
    case 'timeline': {
      // data: { year, count }[]
      return {
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: data.map((d: any) => d.year) },
        yAxis: { type: 'value' },
        series: [{ type: 'bar', data: data.map((d: any) => d.count), itemStyle: { color: '#1976d2' } }],
        grid: { left: 60, right: 20, top: 20, bottom: 40 },
      }
    }
    case 'categories': {
      // data: { name, count }[]
      const sorted = [...data].sort((a: any, b: any) => b.count - a.count)
      return {
        tooltip: { trigger: 'axis' },
        yAxis: { type: 'category', data: sorted.map((d: any) => d.name), inverse: true },
        xAxis: { type: 'value' },
        series: [{ type: 'bar', data: sorted.map((d: any) => d.count), itemStyle: { color: '#7b1fa2' } }],
        grid: { left: 160, right: 20, top: 10, bottom: 20 },
      }
    }
    case 'entities': {
      // data: { name, entity_type, count }[]
      const sorted = [...data].sort((a: any, b: any) => b.count - a.count).slice(0, 15)
      return {
        tooltip: { trigger: 'axis' },
        yAxis: { type: 'category', data: sorted.map((d: any) => d.name), inverse: true },
        xAxis: { type: 'value' },
        series: [{ type: 'bar', data: sorted.map((d: any) => d.count), itemStyle: { color: '#00695c' } }],
        grid: { left: 160, right: 20, top: 10, bottom: 20 },
      }
    }
    case 'jornais': {
      // data: { name, count }[]
      const sorted = [...data].sort((a: any, b: any) => b.count - a.count).slice(0, 15)
      return {
        tooltip: { trigger: 'axis' },
        yAxis: { type: 'category', data: sorted.map((d: any) => d.name), inverse: true },
        xAxis: { type: 'value' },
        series: [{ type: 'bar', data: sorted.map((d: any) => d.count), itemStyle: { color: '#e65100' } }],
        grid: { left: 180, right: 20, top: 10, bottom: 20 },
      }
    }
    case 'gender': {
      // data: { year, gender, count }[] OR { year, M, F }[] (from gender-timeline)
      const years = [...new Set(data.map((d: any) => d.year as string))].sort() as string[]
      let maleData: number[], femaleData: number[]
      if (data[0]?.M !== undefined) {
        // { year, M, F }[] format
        maleData = years.map((y) => data.find((d: any) => d.year === y)?.M || 0)
        femaleData = years.map((y) => data.find((d: any) => d.year === y)?.F || 0)
      } else {
        maleData = years.map((y) => data.find((d: any) => d.year === y && d.gender === 'M')?.count || 0)
        femaleData = years.map((y) => data.find((d: any) => d.year === y && d.gender === 'F')?.count || 0)
      }
      // Normalize to 100%
      const malePct = maleData.map((m, i) => { const t = m + (femaleData[i] || 0); return t ? Math.round((m / t) * 1000) / 10 : 0 })
      const femalePct = femaleData.map((f, i) => { const t = (maleData[i] || 0) + f; return t ? Math.round((f / t) * 1000) / 10 : 0 })
      return {
        tooltip: { trigger: 'axis', formatter: (params: any) => {
          if (!Array.isArray(params)) return ''
          const year = params[0]?.axisValue || ''
          const idx = years.indexOf(year)
          const m = maleData[idx] || 0
          const f = femaleData[idx] || 0
          return params.map((p: any) =>
            `<span style="color:${p.color}">●</span> ${p.seriesName}: ${p.value}% (${(p.seriesName === 'Masculino' ? m : f).toLocaleString()})`
          ).join('<br>') + `<br><span style="color:#999">Total: ${(m + f).toLocaleString()}</span>`
        }},
        legend: { data: ['Masculino', 'Feminino'], bottom: 0 },
        xAxis: { type: 'category', data: years, boundaryGap: false },
        yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
        series: [
          { name: 'Masculino', type: 'line', stack: 'gender', data: malePct, areaStyle: { opacity: 0.85 }, lineStyle: { width: 0 }, itemStyle: { color: '#1565c0' }, symbol: 'none', smooth: true },
          { name: 'Feminino', type: 'line', stack: 'gender', data: femalePct, areaStyle: { opacity: 0.85 }, lineStyle: { width: 0 }, itemStyle: { color: '#E65100' }, symbol: 'none', smooth: true },
        ],
        grid: { left: 48, right: 20, top: 16, bottom: 40 },
      }
    }
    case 'gender-pie': {
      // data: { M: number, F: number }
      return {
        tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
        series: [{
          type: 'pie',
          radius: ['40%', '70%'],
          data: [
            { name: 'Masculino', value: data.M, itemStyle: { color: '#1565c0' } },
            { name: 'Feminino', value: data.F, itemStyle: { color: '#E65100' } },
          ],
          label: { formatter: '{b}\n{d}%' },
        }],
      }
    }
    case 'gender-jornais': {
      // data: { name, M, F }[] — already sorted by proportion from the API
      const names = data.map((d: any) => d.name)
      const mPct = data.map((d: any) => { const t = d.M + d.F; return t ? Math.round(d.M / t * 100) : 0 })
      const fPct = data.map((d: any) => { const t = d.M + d.F; return t ? Math.round(d.F / t * 100) : 0 })
      return {
        tooltip: { trigger: 'axis', formatter: (params: any) => {
          const name = params[0]?.axisValue || ''
          const d = data.find((s: any) => s.name === name)
          return `<b>${name}</b><br>` + params.map((p: any) => `${p.seriesName}: ${p.value}% (${p.seriesName === 'Masculino' ? d?.M : d?.F})`).join('<br>')
        }},
        legend: { data: ['Masculino', 'Feminino'], top: 0 },
        yAxis: { type: 'category', data: names, inverse: true, axisLabel: { width: 100, overflow: 'truncate', fontSize: 11 } },
        xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
        series: [
          { name: 'Masculino', type: 'bar', stack: 'total', data: mPct, itemStyle: { color: '#1565c0' }, label: { show: false } },
          { name: 'Feminino', type: 'bar', stack: 'total', data: fPct, itemStyle: { color: '#E65100' }, label: { show: false } },
        ],
        grid: { left: 120, right: 30, top: 50, bottom: 40 },
      }
    }
    case 'gender-speakers': {
      // data: { name, count }[]
      const sorted = [...data].sort((a: any, b: any) => b.count - a.count).slice(0, 10)
      const color = props.viz.gender === 'F' ? '#E65100' : '#1565c0'
      return {
        tooltip: { trigger: 'axis' },
        yAxis: { type: 'category', data: sorted.map((d: any) => d.name), inverse: true, axisLabel: { width: 120, overflow: 'truncate' } },
        xAxis: { type: 'value' },
        series: [{ type: 'bar', data: sorted.map((d: any) => d.count), itemStyle: { color } }],
        grid: { left: '35%', right: 20, top: 10, bottom: 20 },
      }
    }
    case 'calendar': {
      // data: { date, count }[]
      if (!data.length) return null
      const max = Math.max(...data.map((d: any) => d.count))
      return {
        tooltip: { formatter: (p: any) => `${p.value[0]}: ${p.value[1]}` },
        visualMap: { min: 0, max, show: false, inRange: { color: ['#ebedf0', '#1976d2'] } },
        calendar: { range: [data[0].date.slice(0, 4)], cellSize: ['auto', 13] },
        series: [{ type: 'heatmap', coordinateSystem: 'calendar', data: data.map((d: any) => [d.date, d.count]) }],
      }
    }
    case 'desertos-timeline': {
      // data: { year, active, closures }[]
      const years = data.map((d: any) => d.year)
      const values = data.map((d: any) => d.active)
      return {
        tooltip: { trigger: 'axis', formatter: (params: any) => `<b>${params[0]?.axisValue}</b><br>Jornais ativos: ${params[0]?.value}` },
        xAxis: { type: 'category', data: years, axisLabel: { interval: 4 } },
        yAxis: { type: 'value', name: 'Jornais ativos' },
        series: [{ type: 'bar', data: values, itemStyle: { color: '#1565c0' } }],
        grid: { left: 60, right: 20, top: 40, bottom: 30 },
      }
    }
    case 'desertos-closures': {
      // data: { year, active, closures, openings }[]
      const years = data.map((d: any) => d.year)
      const openings = data.map((d: any) => d.openings || 0)
      const closures = data.map((d: any) => -(d.closures || 0))
      return {
        tooltip: { trigger: 'axis', formatter: (params: any) => {
          const year = params[0]?.axisValue
          const lines = params.map((p: any) => `${p.marker} ${p.seriesName}: ${Math.abs(p.value)}`)
          return `<b>${year}</b><br>${lines.join('<br>')}`
        }},
        legend: { data: ['Aberturas', 'Encerramentos'], top: 0 },
        xAxis: { type: 'category', data: years, axisLabel: { interval: 4 } },
        yAxis: { type: 'value', axisLabel: { formatter: (v: number) => String(Math.abs(v)) } },
        series: [
          { name: 'Aberturas', type: 'bar', data: openings, itemStyle: { color: '#2e7d32' } },
          { name: 'Encerramentos', type: 'bar', data: closures, itemStyle: { color: '#E65100' } },
        ],
        grid: { left: 60, right: 20, top: 50, bottom: 30 },
      }
    }
    case 'desertos-ratio': {
      // data: { year, articles, active, ratio }[]
      const years = data.map((d: any) => d.year)
      const ratios = data.map((d: any) => d.ratio)
      return {
        tooltip: { trigger: 'axis', formatter: (params: any) => {
          const idx = params[0]?.dataIndex
          const d = data[idx]
          return `<b>${params[0]?.axisValue}</b><br>Artigos/jornal: ${params[0]?.value}<br><span class="text-caption">(${d?.articles} artigos ÷ ${d?.active} jornais)</span>`
        }},
        xAxis: { type: 'category', data: years, axisLabel: { interval: 4 } },
        yAxis: { type: 'value', name: 'Artigos por jornal' },
        series: [{ type: 'line', data: ratios, itemStyle: { color: '#2e7d32' }, areaStyle: { opacity: 0.15 }, smooth: true }],
        grid: { left: 60, right: 20, top: 40, bottom: 30 },
      }
    }
    default:
      return null
  }
})
</script>

<style scoped>
.analise-viz {
  width: 100%;
}
</style>
