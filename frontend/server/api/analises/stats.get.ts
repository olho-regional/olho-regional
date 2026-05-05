import { sql } from 'drizzle-orm'

/**
 * GET /api/analises/stats?search=...&year_from=...&year_to=...&distrito=...&jornal=...&author=...
 *
 * Lightweight endpoint that returns total article count, distinct jornal count,
 * and distinct distrito count for the given filters. Used by the analises system
 * to show header stats without hitting the heavier facets endpoint.
 */
export default defineEventHandler(async (event) => {
  const db = useDB(event)
  const query = getQuery(event)

  const search = query.search as string | undefined
  const distrito = query.distrito as string | undefined
  const jornal = query.jornal as string | undefined
  const author = query.author as string | undefined
  const yearFrom = query.year_from as string | undefined
  const yearTo = query.year_to as string | undefined

  // Build filter conditions
  const filterClauses: ReturnType<typeof sql>[] = []
  if (distrito) filterClauses.push(sql`jd.distrito_codigoine = ${distrito}`)
  if (jornal) filterClauses.push(sql`j.nome = ${jornal}`)
  if (author) filterClauses.push(sql`n.author = ${author}`)
  if (yearFrom) filterClauses.push(sql`n.date >= ${`${yearFrom}-01-01`}`)
  if (yearTo) filterClauses.push(sql`n.date <= ${`${yearTo}-12-31`}`)

  const distritoJoin = distrito
    ? sql`JOIN jornais_distritos jd ON jd.jornal_id = j.id`
    : sql``

  if (search) {
    const ftsMatch = search.split(/\s+/).filter(Boolean).map(w => `"${w.replace(/"/g, '')}"`).join(' ')
    const extraWhere = filterClauses.length > 0
      ? sql` AND ${sql.join(filterClauses, sql` AND `)}`
      : sql``

    const [row] = await db.all<{ total: number; jornais: number; distritos: number }>(sql`
      SELECT
        count(DISTINCT n.id) as total,
        count(DISTINCT j.id) as jornais,
        count(DISTINCT jd2.distrito_codigoine) as distritos
      FROM noticias_fts
      JOIN noticias n ON n.rowid = noticias_fts.rowid
      LEFT JOIN jornais j ON n.jornal_id = j.id
      LEFT JOIN jornais_distritos jd2 ON jd2.jornal_id = j.id
      ${distritoJoin}
      WHERE noticias_fts MATCH ${ftsMatch} ${extraWhere}
    `)

    return { total: row?.total || 0, jornais: row?.jornais || 0, distritos: row?.distritos || 0 }
  }

  // Non-FTS path
  const whereClause = filterClauses.length > 0
    ? sql`WHERE ${sql.join(filterClauses, sql` AND `)}`
    : sql``

  const [row] = await db.all<{ total: number; jornais: number; distritos: number }>(sql`
    SELECT
      count(DISTINCT n.id) as total,
      count(DISTINCT j.id) as jornais,
      count(DISTINCT jd2.distrito_codigoine) as distritos
    FROM noticias n
    LEFT JOIN jornais j ON n.jornal_id = j.id
    LEFT JOIN jornais_distritos jd2 ON jd2.jornal_id = j.id
    ${distritoJoin}
    ${whereClause}
  `)

  return { total: row?.total || 0, jornais: row?.jornais || 0, distritos: row?.distritos || 0 }
})
