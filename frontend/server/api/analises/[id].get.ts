import { readFileSync, existsSync } from 'fs'
import { join } from 'path'
import type { AnaliseSource, AnaliseCompiled, VizSource, AnaliseFilters } from '~/types/analise'

function mergeFilters(...sets: (AnaliseFilters | undefined)[]): AnaliseFilters {
  const r: AnaliseFilters = {}
  for (const f of sets) {
    if (!f) continue
    if (f.search) r.search = f.search
    if (f.distrito) r.distrito = f.distrito
    if (f.jornal) r.jornal = f.jornal
    if (f.author) r.author = f.author
    if (f.year_from) r.year_from = f.year_from
    if (f.year_to) r.year_to = f.year_to
  }
  return r
}

function buildQS(filters: AnaliseFilters, extra?: Record<string, string>): string {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(filters)) { if (v) p.set(k, v) }
  if (extra) { for (const [k, v] of Object.entries(extra)) p.set(k, v) }
  return p.toString()
}

async function fetchInternal(event: any, path: string, qs: string) {
  const url = `${path}${qs ? '?' + qs : ''}`
  // Use $fetch which in Nitro server context calls handlers directly
  return $fetch(url, { headers: { host: getRequestURL(event).host } })
}

async function compileViz(event: any, viz: VizSource, filters: AnaliseFilters): Promise<any> {
  const qs = (extra?: Record<string, string>) => buildQS(filters, extra)

  switch (viz.type) {
    case 'timeline': {
      const r: any = await fetchInternal(event, '/api/noticias', qs({ per_page: '1' }))
      return { type: 'timeline', title: viz.title, caption: viz.caption, data: r.yearCounts }
    }
    case 'categories': {
      const r: any = await fetchInternal(event, '/api/noticias/facets', qs({ include: 'labels' }))
      return { type: 'categories', title: viz.title, caption: viz.caption, data: r.labelCounts }
    }
    case 'map': {
      const r: any = await fetchInternal(event, '/api/noticias/facets', qs({ include: 'distritos' }))
      return { type: 'map', title: viz.title, caption: viz.caption, data: r.distritoCounts }
    }
    case 'entities': {
      const extra: Record<string, string> = {}
      if (viz.entity_type) extra.entity_type = viz.entity_type
      const r: any = await fetchInternal(event, '/api/noticias/entities', qs(extra))
      return { type: 'entities', title: viz.title, caption: viz.caption, entity_type: viz.entity_type, data: r.topEntities }
    }
    case 'jornais': {
      const r: any = await fetchInternal(event, '/api/noticias/facets', qs({ include: 'jornais' }))
      return { type: 'jornais', title: viz.title, caption: viz.caption, data: r.jornalCounts }
    }
    case 'calendar': {
      const r: any = await fetchInternal(event, '/api/noticias/facets', qs({ include: 'calendar' }))
      return { type: 'calendar', title: viz.title, caption: viz.caption, data: r.dateCounts }
    }
    case 'map-comparison': {
      if (!viz.series?.length) return { type: 'map-comparison', title: viz.title, caption: viz.caption, data: null }
      const seriesResults = await Promise.all(viz.series.map(async (s) => {
        const seriesFilters = { ...filters, ...s.filters }
        const params = { ...seriesFilters, ...(s.params || {}) }
        const seriesQs = buildQS(params as any)
        const endpoint = s.endpoint || '/api/analises/gender-map'
        const r: any = await fetchInternal(event, endpoint, seriesQs)
        return { label: s.label, years: r.years, districts: r.districts }
      }))
      return { type: 'map-comparison', title: viz.title, caption: viz.caption, data: { animated: viz.animated ?? false, hues: viz.hues, geojsonUrl: viz.geojsonUrl, labelField: viz.labelField, countLabel: viz.countLabel, series: seriesResults } }
    }
    case 'desertos-timeline':
    case 'desertos-closures': {
      const r: any = await fetchInternal(event, '/api/analises/desertos-timeline', '')
      return { type: viz.type, title: viz.title, caption: viz.caption, data: r.data }
    }
    case 'desertos-ratio': {
      const r: any = await fetchInternal(event, '/api/analises/desertos-ratio', '')
      return { type: 'desertos-ratio', title: viz.title, caption: viz.caption, data: r.data }
    }
    case 'gender-keywords': {
      const keywords = viz.keywords || []
      const results: Record<string, any> = {}
      for (const kw of keywords) {
        const kwFilters = { ...filters, search: kw, year_from: '2015', year_to: '2026' }
        const kwQs = buildQS(kwFilters as any)
        const r: any = await fetchInternal(event, '/api/analises/gender-timeline', kwQs)
        results[kw] = r.data
      }
      return { type: 'gender-keywords', title: viz.title, caption: viz.caption, data: { keywords, results } }
    }
    case 'gender-pie': {
      const extra: Record<string, string> = {}
      if (viz.exclude_top) extra.exclude_top = String(viz.exclude_top)
      const r: any = await fetchInternal(event, '/api/analises/gender-totals', qs(extra))
      return { type: 'gender-pie', title: viz.title, caption: viz.caption, data: r }
    }
    case 'gender-jornais': {
      const extra: Record<string, string> = { gender: viz.gender || 'M' }
      if (viz.exclude_top) extra.exclude_top = String(viz.exclude_top)
      const r: any = await fetchInternal(event, '/api/analises/gender-jornais', qs(extra))
      return { type: 'gender-jornais', title: viz.title, caption: viz.caption, gender: viz.gender, data: r.jornais }
    }
    case 'gender-speakers': {
      const extra: Record<string, string> = { gender: viz.gender || 'M' }
      const r: any = await fetchInternal(event, '/api/analises/gender-speakers', qs(extra))
      return { type: 'gender-speakers', title: viz.title, caption: viz.caption, gender: viz.gender, data: r.speakers }
    }
    case 'gender': {
      // Use dedicated timeline endpoint if exclude_top is set
      if (viz.exclude_top) {
        const extra: Record<string, string> = { exclude_top: String(viz.exclude_top) }
        const r: any = await fetchInternal(event, '/api/analises/gender-timeline', qs(extra))
        return { type: 'gender', title: viz.title, caption: viz.caption, exclude_top: viz.exclude_top, data: r.data }
      }
      const r: any = await fetchInternal(event, '/api/noticias/facets', qs({ include: 'gender' }))
      return { type: 'gender', title: viz.title, caption: viz.caption, data: r.genderByYear }
    }
    default:
      return { type: viz.type, title: viz.title, caption: viz.caption, data: null }
  }
}

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  if (!id || /[^a-z0-9-]/.test(id)) {
    throw createError({ statusCode: 400, statusMessage: 'Invalid analysis ID' })
  }

  // Dev mode: compile on the fly from source
  const publicDir = join(process.cwd(), 'public', 'analises')
  let sourcePath = join(publicDir, `${id}.json`)
  let devMode = false
  try {
    if (existsSync(sourcePath)) {
      devMode = true
    } else {
      // Filename may have a numeric prefix (e.g. 03-gastronomia-regional.json)
      const { readdirSync } = await import('fs')
      const match = readdirSync(publicDir).find(f => f.endsWith(`-${id}.json`))
      if (match) {
        sourcePath = join(publicDir, match)
        devMode = true
      }
    }
  } catch {
    // fs not available on edge
  }

  if (!devMode) {
    // Production (Cloudflare Pages): fetch the static compiled file
    const url = getRequestURL(event)
    const baseUrl = `${url.protocol}//${url.host}`
    try {
      return await $fetch(`${baseUrl}/analises/_compiled/${id}.json`)
    } catch {
      throw createError({ statusCode: 404, statusMessage: `Analysis not found: ${id}` })
    }
  }

  const source: AnaliseSource = JSON.parse(readFileSync(sourcePath, 'utf-8'))

  // Build stats from the analysis' global filters (what the analysis is about)
  const globalFilters = source.filters || {}
  const analiseStats: any = await fetchInternal(event, '/api/analises/stats', buildQS(globalFilters))

  const stats = [
    { label: 'Notícias', value: (analiseStats.total || 0).toLocaleString('pt-PT') },
    { label: 'Jornais com notícias', value: analiseStats.jornais || 0 },
  ]

  const compiledSteps = []
  for (const step of source.steps) {
    const stepFilters = mergeFilters(source.filters, step.filters)

    if (step.type === 'text') {
      compiledSteps.push({ id: step.id, type: step.type, title: step.title, text: step.text })
      continue
    }

    if (step.type === 'split' && step.viz) {
      const vizFilters = mergeFilters(stepFilters, step.viz.filters)
      const compiled = await compileViz(event, step.viz, vizFilters)
      compiledSteps.push({ id: step.id, type: step.type, title: step.title, text: step.text, layout: step.layout, viz: compiled })
      continue
    }

    if (step.type === 'side-by-side' && step.vizzes) {
      const compiledVizzes = []
      for (const viz of step.vizzes) {
        const vizFilters = mergeFilters(stepFilters, viz.filters)
        compiledVizzes.push(await compileViz(event, viz, vizFilters))
      }
      compiledSteps.push({ id: step.id, type: step.type, title: step.title, text: step.text, vizzes: compiledVizzes })
      continue
    }

    compiledSteps.push({ id: step.id, type: step.type, title: step.title, text: step.text })
  }

  return {
    id: source.id,
    title: source.title,
    description: source.description,
    backgroundColor: source.backgroundColor,
    backgroundImage: source.backgroundImage,
    stats,
    steps: compiledSteps,
  } satisfies AnaliseCompiled
})
