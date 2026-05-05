/**
 * Type definitions for analysis example pages.
 *
 * Source files: public/analises/<id>.json (hand-edited, filters + viz types)
 * Compiled files: public/analises/_compiled/<id>.json (built with data baked in)
 */

/** Shared filter parameters matching the API query params */
export interface AnaliseFilters {
  search?: string
  distrito?: string
  jornal?: string
  author?: string
  year_from?: string
  year_to?: string
}

/** Available visualization types (mirrors analisar page sections) */
export type VizType =
  | 'timeline'       // articles per year (bar chart)
  | 'categories'     // topic/label distribution (horizontal bar)
  | 'map'            // district choropleth
  | 'map-comparison' // side-by-side maps with optional time animation
  | 'entities'       // top entities list (bar)
  | 'gender'         // gender balance over time (stacked area)
  | 'gender-pie'     // gender totals pie chart
  | 'gender-jornais' // top jornais by gender distribution (stacked 100%)
  | 'gender-speakers'// top speakers by gender
  | 'jornais'        // per-newspaper distribution (bar)
  | 'calendar'       // daily heatmap
  | 'desertos-timeline' // active jornais per year (bar)
  | 'desertos-closures' // jornal closures per year (bar)
  | 'desertos-ratio'    // articles per active jornal per year (line)
  | 'gender-keywords'   // gender evolution filtered by keyword chips

/** Visualization declaration in the source JSON */
export interface VizSource {
  type: VizType
  /** Override the default title for this viz */
  title?: string
  /** Optional caption below */
  caption?: string
  /** Override filters just for this viz (merged with step filters) */
  filters?: AnaliseFilters
  /** For entities: filter by type */
  entity_type?: 'PER' | 'ORG'
  /** For map-comparison: series definitions (each gets its own map panel) */
  series?: MapComparisonSeries[]
  /** For map-comparison: enable year-by-year animation */
  animated?: boolean
  /** For map-comparison: color hue per series (css hsl hue value) */
  hues?: number[]
  /** For map-comparison: custom GeoJSON URL (default: /portugal-distritos.json) */
  geojsonUrl?: string
  /** For map-comparison: GeoJSON property to use as label (default: 'distrito') */
  labelField?: string
  /** For map-comparison: label for the count in tooltips (default: 'citações') */
  countLabel?: string
  /** For gender-speakers: which gender to show */
  gender?: 'M' | 'F'
  /** For gender/gender-speakers: exclude top N speakers from counts */
  exclude_top?: number
  /** For gender-keywords: list of keyword queries to show as chips */
  keywords?: string[]
}

/** A single series in a map-comparison viz */
export interface MapComparisonSeries {
  /** Label shown above the map panel */
  label: string
  /** Filter override for this series (e.g. gender=M) */
  filters?: AnaliseFilters
  /** Arbitrary query params for custom endpoints */
  params?: Record<string, string>
  /** Custom API endpoint (default: /api/analises/gender-map) */
  endpoint?: string
}

/** Compiled visualization (source + resolved data) */
export interface VizCompiled extends VizSource {
  data: any
}

/** A step in the source JSON (what you hand-edit) */
export interface AnaliseStepSource {
  id: string
  type: 'text' | 'split' | 'side-by-side'
  title?: string
  text?: string
  /** For 'split': which side the viz goes on */
  layout?: 'viz-left' | 'viz-right'
  /** Filters applied to all vizzes in this step */
  filters?: AnaliseFilters
  /** For 'split': single viz */
  viz?: VizSource
  /** For 'side-by-side': multiple vizzes */
  vizzes?: VizSource[]
}

/** A step in the compiled JSON (with data baked in) */
export interface AnaliseStepCompiled {
  id: string
  type: 'text' | 'split' | 'side-by-side'
  title?: string
  text?: string
  layout?: 'viz-left' | 'viz-right'
  viz?: VizCompiled
  vizzes?: VizCompiled[]
}

/** Source config (what you edit in public/analises/<id>.json) */
export interface AnaliseSource {
  id: string
  title: string
  description?: string
  backgroundColor?: string
  backgroundImage?: string
  /** Global filters applied to all steps (can be overridden per step/viz) */
  filters?: AnaliseFilters
  steps: AnaliseStepSource[]
}

/** Compiled config (output of build script, served in production) */
export interface AnaliseCompiled {
  id: string
  title: string
  description?: string
  backgroundColor?: string
  backgroundImage?: string
  /** DB stats at build time */
  stats: Array<{ label: string; value: string | number }>
  steps: AnaliseStepCompiled[]
}
