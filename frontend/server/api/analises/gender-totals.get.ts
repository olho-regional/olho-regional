import { sql } from 'drizzle-orm'

/**
 * GET /api/analises/gender-totals
 *
 * Returns total quote counts by gender. Lightweight.
 * Optional: search, year_from, year_to, distrito, jornal, exclude_top
 *
 * Response: { M: number, F: number }
 */
export default defineEventHandler(async (event) => {
  const db = useDB(event)
  const query = getQuery(event)

  const search = query.search as string | undefined
  const yearFrom = query.year_from as string | undefined
  const yearTo = query.year_to as string | undefined
  const excludeTop = query.exclude_top ? parseInt(query.exclude_top as string) : undefined

  const filterClauses: ReturnType<typeof sql>[] = []
  if (yearFrom) filterClauses.push(sql`n.date >= ${`${yearFrom}-01-01`}`)
  if (yearTo) filterClauses.push(sql`n.date <= ${`${yearTo}-12-31`}`)

  // If excluding top N speakers, get their names first
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
    const ftsMatch = search.split(/\s+/).filter(Boolean).map(w => `"${w.replace(/"/g, '')}"`).join(' ')
    const extraWhere = filterClauses.length > 0
      ? sql` AND ${sql.join(filterClauses, sql` AND `)}`
      : sql``

    const rows = await db.all<{ gender: string; count: number }>(sql`
      SELECT q.gender, count(*) as count
      FROM noticias_fts
      JOIN noticias n ON n.rowid = noticias_fts.rowid
      JOIN quotes q ON q.noticia_id = n.id
      WHERE noticias_fts MATCH ${ftsMatch} ${extraWhere} ${excludeClause}
      GROUP BY q.gender
    `)

    const result: Record<string, number> = { M: 0, F: 0 }
    for (const r of rows) result[r.gender] = r.count
    return result
  }

  // Non-FTS
  const whereClause = filterClauses.length > 0
    ? sql`WHERE ${sql.join(filterClauses, sql` AND `)} ${excludeClause}`
    : excludeTop ? sql`WHERE 1=1 ${excludeClause}` : sql``

  const joinN = (filterClauses.length > 0)
    ? sql`JOIN noticias n ON q.noticia_id = n.id`
    : sql``

  const rows = await db.all<{ gender: string; count: number }>(sql`
    SELECT q.gender, count(*) as count
    FROM quotes q
    ${joinN}
    ${whereClause}
    GROUP BY q.gender
  `)

  const result: Record<string, number> = { M: 0, F: 0 }
  for (const r of rows) result[r.gender] = r.count
  return result
})
