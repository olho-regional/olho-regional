import { sql } from 'drizzle-orm'

/**
 * GET /api/analises/desertos-ratio
 *
 * Returns articles per year divided by active jornais count that year.
 * Response: { data: { year: string, articles: number, active: number, ratio: number }[] }
 */
export default defineEventHandler(async (event) => {
  const db = useDB(event)

  // Get articles per year
  const articleRows = await db.all<{ year: string; count: number }>(sql`
    SELECT substr(date, 1, 4) as year, count(*) as count
    FROM noticias
    WHERE date IS NOT NULL AND length(date) >= 4
    GROUP BY year ORDER BY year
  `)

  // Get jornais lifecycle data
  const jornais = await db.all<{
    data_inscricao: string | null
    data_situacao: string | null
    estado: string | null
  }>(sql`
    SELECT data_inscricao, data_situacao, estado FROM jornais WHERE data_inscricao IS NOT NULL
  `)

  const minYear = 1996
  const maxYear = new Date().getFullYear()

  // Count active jornais per year
  const activeCounts: Record<string, number> = {}
  for (let y = minYear; y <= maxYear; y++) activeCounts[String(y)] = 0

  for (const j of jornais) {
    const startYear = parseInt(j.data_inscricao!.slice(0, 4))
    const isInactive = j.estado?.toLowerCase() === 'inativo'
    const endYear = isInactive && j.data_situacao
      ? parseInt(j.data_situacao.slice(0, 4))
      : maxYear + 1

    for (let y = Math.max(startYear, minYear); y <= Math.min(endYear, maxYear); y++) {
      activeCounts[String(y)]++
    }
  }

  // Build article count map
  const articleMap: Record<string, number> = {}
  for (const r of articleRows) articleMap[r.year] = r.count

  // Build result
  const data = []
  for (let y = minYear; y <= maxYear; y++) {
    const ys = String(y)
    const articles = articleMap[ys] || 0
    const active = activeCounts[ys] || 0
    data.push({
      year: ys,
      articles,
      active,
      ratio: active > 0 ? Math.round(articles / active) : 0,
    })
  }

  return { data }
})
