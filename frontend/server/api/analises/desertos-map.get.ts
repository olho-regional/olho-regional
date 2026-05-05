import { sql } from 'drizzle-orm'

/**
 * GET /api/analises/desertos-map?level=distrito|municipio
 *
 * Returns active and newly-inactive jornais count per year per geographic area.
 * Used for the animated map-comparison in the "desertos de notícias" analysis.
 *
 * Response: { years: string[], districts: Record<string, Record<string, number>> }
 * (districts keyed by distrito/municipio name, values are { year: count })
 */
export default defineEventHandler(async (event) => {
  const db = useDB(event)
  const query = getQuery(event)
  const level = (query.level as string) || 'distrito'
  const metric = (query.metric as string) || 'active' // 'active' | 'inactive'

  // Get all jornais with geographic associations and dates
  const geoJoin = level === 'municipio'
    ? sql`JOIN jornais_municipios jg ON jg.jornal_id = j.id JOIN municipios g ON g.codigoine = jg.municipio_codigoine`
    : sql`JOIN jornais_distritos jg ON jg.jornal_id = j.id JOIN distritos g ON g.codigoine = jg.distrito_codigoine`

  const rows = await db.all<{
    geo_name: string
    data_inscricao: string | null
    data_situacao: string | null
    estado: string | null
  }>(sql`
    SELECT g.nome as geo_name, j.data_inscricao, j.data_situacao, j.estado
    FROM jornais j
    ${geoJoin}
    WHERE j.data_inscricao IS NOT NULL
  `)

  // Determine year range
  const minYear = 1996
  const maxYear = new Date().getFullYear()
  const years: string[] = []
  for (let y = minYear; y <= maxYear; y++) years.push(String(y))

  // Build per-geo, per-year counts
  const districts: Record<string, Record<string, number>> = {}

  for (const row of rows) {
    const geo = row.geo_name
    if (!geo) continue
    if (!districts[geo]) districts[geo] = {}

    const startYear = parseInt(row.data_inscricao!.slice(0, 4))
    const isInactive = row.estado?.toLowerCase() === 'inativo'
    const endYear = isInactive && row.data_situacao
      ? parseInt(row.data_situacao.slice(0, 4))
      : maxYear + 1 // still active

    if (metric === 'active') {
      // Count as active for each year it was active
      for (let y = Math.max(startYear, minYear); y <= Math.min(endYear, maxYear); y++) {
        const ys = String(y)
        districts[geo][ys] = (districts[geo][ys] || 0) + 1
      }
    } else {
      // Count as newly inactive in the year it became inactive
      if (isInactive && endYear >= minYear && endYear <= maxYear) {
        const ys = String(endYear)
        districts[geo][ys] = (districts[geo][ys] || 0) + 1
      }
    }
  }

  return { years, districts }
})
