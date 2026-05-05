import { sql } from 'drizzle-orm'

/**
 * GET /api/analises/desertos-timeline
 *
 * Returns total active jornais, closures, and openings per year.
 * Response: { data: { year: string, active: number, closures: number, openings: number }[] }
 */
export default defineEventHandler(async (event) => {
  const db = useDB(event)

  const rows = await db.all<{
    data_inscricao: string | null
    data_situacao: string | null
    estado: string | null
  }>(sql`
    SELECT data_inscricao, data_situacao, estado
    FROM jornais
    WHERE data_inscricao IS NOT NULL
  `)

  const minYear = 1996
  const maxYear = new Date().getFullYear()
  const activeCounts: Record<string, number> = {}
  const closureCounts: Record<string, number> = {}
  const openingCounts: Record<string, number> = {}

  for (let y = minYear; y <= maxYear; y++) {
    activeCounts[String(y)] = 0
    closureCounts[String(y)] = 0
    openingCounts[String(y)] = 0
  }

  for (const row of rows) {
    const startYear = parseInt(row.data_inscricao!.slice(0, 4))
    const isInactive = row.estado?.toLowerCase() === 'inativo'
    const endYear = isInactive && row.data_situacao
      ? parseInt(row.data_situacao.slice(0, 4))
      : maxYear + 1

    for (let y = Math.max(startYear, minYear); y <= Math.min(endYear, maxYear); y++) {
      activeCounts[String(y)]++
    }

    // Count opening in the year it was registered
    if (startYear >= minYear && startYear <= maxYear) {
      openingCounts[String(startYear)]++
    }

    // Count closure in the year it became inactive
    if (isInactive && row.data_situacao) {
      const closureYear = parseInt(row.data_situacao.slice(0, 4))
      if (closureYear >= minYear && closureYear <= maxYear) {
        closureCounts[String(closureYear)]++
      }
    }
  }

  const data = Object.keys(activeCounts)
    .sort()
    .map(year => ({ year, active: activeCounts[year], closures: closureCounts[year], openings: openingCounts[year] }))

  return { data }
})
