import { sql } from 'drizzle-orm'

/**
 * GET /api/analises/gender-speakers?gender=M&limit=10
 *
 * Returns top N most cited speakers for a given gender.
 * Optional: search, year_from, year_to
 *
 * Response: { speakers: { name: string, count: number }[] }
 */
export default defineEventHandler(async (event) => {
  const db = useDB(event)
  const query = getQuery(event)

  const gender = (query.gender as string) || 'M'
  const limit = Math.min(parseInt(query.limit as string) || 10, 30)
  const search = query.search as string | undefined
  const yearFrom = query.year_from as string | undefined
  const yearTo = query.year_to as string | undefined

  const filterClauses: ReturnType<typeof sql>[] = []
  filterClauses.push(sql`q.gender = ${gender}`)
  if (yearFrom) filterClauses.push(sql`n.date >= ${`${yearFrom}-01-01`}`)
  if (yearTo) filterClauses.push(sql`n.date <= ${`${yearTo}-12-31`}`)

  if (search) {
    const ftsMatch = search.split(/\s+/).filter(Boolean).map(w => `"${w.replace(/"/g, '')}"`).join(' ')
    const extraWhere = filterClauses.length > 0
      ? sql` AND ${sql.join(filterClauses, sql` AND `)}`
      : sql``

    const rows = await db.all<{ name: string; count: number }>(sql`
      SELECT q.speaker as name, count(*) as count
      FROM noticias_fts
      JOIN noticias n ON n.rowid = noticias_fts.rowid
      JOIN quotes q ON q.noticia_id = n.id
      WHERE noticias_fts MATCH ${ftsMatch} ${extraWhere}
      GROUP BY q.speaker ORDER BY count DESC LIMIT ${limit}
    `)

    return { speakers: rows }
  }

  // Non-FTS path
  const joinN = (yearFrom || yearTo)
    ? sql`JOIN noticias n ON q.noticia_id = n.id`
    : sql``
  const whereClause = sql`WHERE ${sql.join(filterClauses, sql` AND `)}`

  const rows = await db.all<{ name: string; count: number }>(sql`
    SELECT q.speaker as name, count(*) as count
    FROM quotes q
    ${joinN}
    ${whereClause}
    GROUP BY q.speaker ORDER BY count DESC LIMIT ${limit}
  `)

  return { speakers: rows }
})
