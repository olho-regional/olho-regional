import { sql } from 'drizzle-orm'

/**
 * GET /api/analises/gender-timeline?exclude_top=200
 *
 * Returns gender counts by year, optionally excluding top N speakers.
 * Optional: search, year_from, year_to, exclude_top
 *
 * Response: { data: { year: string, M: number, F: number }[] }
 */
export default defineEventHandler(async (event) => {
  const db = useDB(event)
  const query = getQuery(event)

  const search = query.search as string | undefined
  const yearFrom = query.year_from as string | undefined
  const yearTo = query.year_to as string | undefined
  const excludeTop = query.exclude_top ? parseInt(query.exclude_top as string) : undefined

  const filterClauses: ReturnType<typeof sql>[] = []
  filterClauses.push(sql`n.date IS NOT NULL AND length(n.date) >= 4`)
  if (yearFrom) filterClauses.push(sql`n.date >= ${`${yearFrom}-01-01`}`)
  if (yearTo) filterClauses.push(sql`n.date <= ${`${yearTo}-12-31`}`)

  let excludeClause = sql``
  if (excludeTop) {
    const topSpeakers = await db.all<{ speaker: string }>(sql`
      SELECT speaker FROM quotes GROUP BY speaker ORDER BY count(*) DESC LIMIT ${excludeTop}
    `)
    if (topSpeakers.length > 0) {
      const names = topSpeakers.map(s => s.speaker)
      excludeClause = sql`AND q.speaker NOT IN (${sql.join(names.map(n => sql`${n}`), sql`, `)})`
    }
  }

  if (search) {
    const ftsMatch = search.split(/\s+/).filter(Boolean).map(w => {
      if (w === 'OR' || w === 'OU') return 'OR'
      return `"${w.replace(/"/g, '')}"`
    }).join(' ')
    const extraWhere = filterClauses.length > 0
      ? sql` AND ${sql.join(filterClauses, sql` AND `)}`
      : sql``

    const rows = await db.all<{ year: string; gender: string; count: number }>(sql`
      SELECT substr(n.date, 1, 4) as year, q.gender, count(*) as count
      FROM noticias_fts
      JOIN noticias n ON n.rowid = noticias_fts.rowid
      JOIN quotes q ON q.noticia_id = n.id
      WHERE noticias_fts MATCH ${ftsMatch} ${extraWhere} ${excludeClause}
      GROUP BY year, q.gender ORDER BY year
    `)

    return { data: buildResult(rows) }
  }

  // Non-FTS path
  const whereClause = sql`WHERE ${sql.join(filterClauses, sql` AND `)} ${excludeClause}`

  const rows = await db.all<{ year: string; gender: string; count: number }>(sql`
    SELECT substr(n.date, 1, 4) as year, q.gender, count(*) as count
    FROM quotes q
    JOIN noticias n ON q.noticia_id = n.id
    ${whereClause}
    GROUP BY year, q.gender ORDER BY year
  `)

  return { data: buildResult(rows) }
})

function buildResult(rows: { year: string; gender: string; count: number }[]) {
  const yearMap: Record<string, { M: number; F: number }> = {}
  for (const r of rows) {
    if (!yearMap[r.year]) yearMap[r.year] = { M: 0, F: 0 }
    if (r.gender === 'M') yearMap[r.year].M = r.count
    else if (r.gender === 'F') yearMap[r.year].F = r.count
  }
  return Object.entries(yearMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([year, counts]) => ({ year, ...counts }))
}
