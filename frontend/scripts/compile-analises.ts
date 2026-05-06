/**
 * Build script: compiles analysis source JSONs into data-baked versions.
 *
 * Reads:   public/analises/<id>.json (source: filters + viz types)
 * Writes:  public/analises/_compiled/<id>.json (compiled: with data)
 *
 * Usage:
 *   npx tsx scripts/compile-analises.ts [--base-url http://localhost:3001]
 */

import { readFileSync, writeFileSync, readdirSync, mkdirSync, existsSync } from 'fs'
import { join } from 'path'

interface Filters {
  search?: string
  distrito?: string
  jornal?: string
  author?: string
  year_from?: string
  year_to?: string
}

interface VizSource {
  type: string
  title?: string
  caption?: string
  filters?: Filters
  entity_type?: string
}

interface StepSource {
  id: string
  type: string
  title?: string
  text?: string
  layout?: string
  filters?: Filters
  viz?: VizSource
  vizzes?: VizSource[]
}

interface AnaliseSource {
  id: string
  title: string
  description?: string
  backgroundColor?: string
  backgroundImage?: string
  filters?: Filters
  steps: StepSource[]
}

const BASE_URL = process.argv.includes('--base-url')
  ? process.argv[process.argv.indexOf('--base-url') + 1]
  : 'http://localhost:3000'

const PUBLIC_DIR = join(import.meta.dirname, '..', 'public', 'analises')
const COMPILED_DIR = join(PUBLIC_DIR, '_compiled')

function mergeFilters(...filterSets: (Filters | undefined)[]): Filters {
  const result: Filters = {}
  for (const f of filterSets) {
    if (!f) continue
    if (f.search) result.search = f.search
    if (f.distrito) result.distrito = f.distrito
    if (f.jornal) result.jornal = f.jornal
    if (f.author) result.author = f.author
    if (f.year_from) result.year_from = f.year_from
    if (f.year_to) result.year_to = f.year_to
  }
  return result
}

function buildQueryString(filters: Filters): string {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(filters)) {
    if (v) params.set(k, v)
  }
  return params.toString()
}

async function fetchJson(path: string, filters: Filters, extra?: Record<string, string>): Promise<any> {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(filters)) {
    if (v) params.set(k, v)
  }
  if (extra) {
    for (const [k, v] of Object.entries(extra)) params.set(k, v)
  }
  const qs = params.toString()
  const url = `${BASE_URL}${path}${qs ? '?' + qs : ''}`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} fetching ${url}`)
  return res.json()
}

async function compileViz(viz: VizSource, filters: Filters): Promise<any> {
  switch (viz.type) {
    case 'timeline': {
      const result = await fetchJson('/api/noticias', { ...filters, per_page: '1' } as any)
      return {
        type: 'timeline',
        title: viz.title,
        caption: viz.caption,
        data: result.yearCounts, // { year, count }[]
      }
    }
    case 'categories': {
      const result = await fetchJson('/api/noticias/facets', filters, { include: 'labels' })
      return {
        type: 'categories',
        title: viz.title,
        caption: viz.caption,
        data: result.labelCounts, // { name, count }[]
      }
    }
    case 'map': {
      const result = await fetchJson('/api/noticias/facets', filters, { include: 'distritos' })
      return {
        type: 'map',
        title: viz.title,
        caption: viz.caption,
        data: result.distritoCounts, // { name, count }[]
      }
    }
    case 'entities': {
      const extra: Record<string, string> = {}
      if (viz.entity_type) extra.entity_type = viz.entity_type
      const result = await fetchJson('/api/noticias/entities', filters, extra)
      return {
        type: 'entities',
        title: viz.title,
        caption: viz.caption,
        entity_type: viz.entity_type,
        data: result.topEntities, // { name, entity_type, count }[]
      }
    }
    case 'gender': {
      if (viz.exclude_top) {
        const extra: Record<string, string> = { exclude_top: String(viz.exclude_top) }
        const result = await fetchJson('/api/analises/gender-timeline', filters, extra)
        return { type: 'gender', title: viz.title, caption: viz.caption, exclude_top: viz.exclude_top, data: result.data }
      }
      const result = await fetchJson('/api/noticias/facets', filters, { include: 'gender' })
      return {
        type: 'gender',
        title: viz.title,
        caption: viz.caption,
        data: result.genderByYear, // { year, gender, count }[]
      }
    }
    case 'gender-pie': {
      const extra: Record<string, string> = {}
      if (viz.exclude_top) extra.exclude_top = String(viz.exclude_top)
      const result = await fetchJson('/api/analises/gender-totals', filters, extra)
      return { type: 'gender-pie', title: viz.title, caption: viz.caption, data: result }
    }
    case 'gender-jornais': {
      const extra: Record<string, string> = { gender: viz.gender || 'M' }
      if (viz.exclude_top) extra.exclude_top = String(viz.exclude_top)
      const result = await fetchJson('/api/analises/gender-jornais', filters, extra)
      return { type: 'gender-jornais', title: viz.title, caption: viz.caption, gender: viz.gender, data: result.jornais }
    }
    case 'gender-speakers': {
      const extra: Record<string, string> = { gender: viz.gender || 'M' }
      const result = await fetchJson('/api/analises/gender-speakers', filters, extra)
      return { type: 'gender-speakers', title: viz.title, caption: viz.caption, gender: viz.gender, data: result.speakers }
    }
    case 'jornais': {
      const result = await fetchJson('/api/noticias/facets', filters, { include: 'jornais' })
      return {
        type: 'jornais',
        title: viz.title,
        caption: viz.caption,
        data: result.jornalCounts, // { name, count }[]
      }
    }
    case 'calendar': {
      const result = await fetchJson('/api/noticias/facets', filters, { include: 'calendar' })
      return {
        type: 'calendar',
        title: viz.title,
        caption: viz.caption,
        data: result.dateCounts, // { date, count }[]
      }
    }
    case 'map-comparison': {
      if (!viz.series?.length) return { type: 'map-comparison', title: viz.title, caption: viz.caption, data: null }
      const seriesResults = await Promise.all(viz.series.map(async (s) => {
        const seriesFilters = { ...filters, ...s.filters }
        const params = { ...seriesFilters, ...(s.params || {}) }
        const endpoint = s.endpoint || '/api/analises/gender-map'
        const result = await fetchJson(endpoint, params as any)
        return { label: s.label, years: result.years, districts: result.districts }
      }))
      return {
        type: 'map-comparison',
        title: viz.title,
        caption: viz.caption,
        data: { animated: viz.animated ?? false, hues: viz.hues, geojsonUrl: viz.geojsonUrl, labelField: viz.labelField, countLabel: viz.countLabel, series: seriesResults },
      }
    }
    case 'desertos-timeline':
    case 'desertos-closures': {
      const result = await fetchJson('/api/analises/desertos-timeline', filters)
      return {
        type: viz.type,
        title: viz.title,
        caption: viz.caption,
        data: result.data,
      }
    }
    case 'desertos-ratio': {
      const result = await fetchJson('/api/analises/desertos-ratio', filters)
      return {
        type: 'desertos-ratio',
        title: viz.title,
        caption: viz.caption,
        data: result.data,
      }
    }
    case 'gender-keywords': {
      const keywords = viz.keywords || []
      const results: Record<string, any> = {}
      for (const kw of keywords) {
        const kwFilters = { ...filters, search: kw, year_from: '2015', year_to: '2026' }
        const r = await fetchJson('/api/analises/gender-timeline', kwFilters)
        results[kw] = r.data
      }
      return {
        type: 'gender-keywords',
        title: viz.title,
        caption: viz.caption,
        data: { keywords, results },
      }
    }
    default:
      console.warn(`  ⚠️  Unknown viz type: ${viz.type}`)
      return { type: viz.type, title: viz.title, caption: viz.caption, data: null }
  }
}

async function compileAnalise(source: AnaliseSource) {
  console.log(`\n  Compiling: ${source.id}`)

  // Build stats from the analysis' global filters
  const globalFilters = source.filters || {}
  const analiseStats = await fetchJson('/api/analises/stats', globalFilters)
  const stats = [
    { label: 'Artigos', value: (analiseStats.total || 0).toLocaleString('pt-PT') },
    { label: 'Jornais', value: analiseStats.jornais || 0 },
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
      const compiled = await compileViz(step.viz, vizFilters)
      compiledSteps.push({
        id: step.id,
        type: step.type,
        title: step.title,
        text: step.text,
        layout: step.layout,
        viz: compiled,
      })
      continue
    }

    if (step.type === 'side-by-side' && step.vizzes) {
      const compiledVizzes = []
      for (const viz of step.vizzes) {
        const vizFilters = mergeFilters(stepFilters, viz.filters)
        compiledVizzes.push(await compileViz(viz, vizFilters))
      }
      compiledSteps.push({
        id: step.id,
        type: step.type,
        title: step.title,
        text: step.text,
        vizzes: compiledVizzes,
      })
      continue
    }

    if (step.type === 'grid' && step.items) {
      const compiledItems = []
      for (const item of step.items) {
        const vizFilters = mergeFilters(stepFilters, item.filters)
        const compiled = await compileViz(item.viz, vizFilters)
        compiledItems.push({ label: item.label, link: item.link, viz: compiled })
      }
      compiledSteps.push({
        id: step.id,
        type: step.type,
        title: step.title,
        text: step.text,
        items: compiledItems,
      })
      continue
    }

    // Fallback: pass through
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
  }
}

async function main() {
  console.log(`Compiling analyses from: ${PUBLIC_DIR}`)
  console.log(`API base: ${BASE_URL}`)

  if (!existsSync(COMPILED_DIR)) mkdirSync(COMPILED_DIR, { recursive: true })

  const files = readdirSync(PUBLIC_DIR).filter(f => f.endsWith('.json'))
  console.log(`Found ${files.length} source file(s)`)

  const index: Array<{ id: string; title: string; description?: string; backgroundColor?: string; backgroundImage?: string }> = []

  for (const file of files) {
    const content = readFileSync(join(PUBLIC_DIR, file), 'utf-8')
    const source: AnaliseSource = JSON.parse(content)

    try {
      const compiled = await compileAnalise(source)
      const outFile = `${source.id}.json`
      const outPath = join(COMPILED_DIR, outFile)
      writeFileSync(outPath, JSON.stringify(compiled, null, 2))
      console.log(`  ✓ Written: _compiled/${outFile}`)

      index.push({
        id: source.id,
        title: source.title,
        description: source.description,
        backgroundColor: source.backgroundColor,
        backgroundImage: source.backgroundImage,
      })
    } catch (e: any) {
      console.error(`  ✗ Failed: ${file} — ${e.message}`)
    }
  }

  // Write index for production edge runtime
  writeFileSync(join(COMPILED_DIR, '_index.json'), JSON.stringify(index, null, 2))
  console.log(`  ✓ Written: _compiled/_index.json`)

  console.log('\nDone!')
}

main()
