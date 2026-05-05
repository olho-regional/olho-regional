import { sql } from 'drizzle-orm'

/**
 * GET /api/analises/gender-jornais?gender=M|F&limit=10
 *
 * Returns top N jornais ranked by the PROPORTION of the target gender in their citations.
 * Only includes jornais with at least 30 total citations (to avoid noise).
 * Returns M and F counts plus articles count for context.
 *
 * Response: { jornais: { name: string, M: number, F: number, articles: number }[] }
 */
export default defineEventHandler(async (event) => {
  const db = useDB(event)
  const query = getQuery(event)

  const gender = (query.gender as string) || 'M'
  const limit = Math.min(parseInt(query.limit as string) || 10, 30)
  const search = query.search as string | undefined
  const yearFrom = query.year_from as string | undefined
  const yearTo = query.year_to as string | undefined
  const excludeTop = query.exclude_top ? parseInt(query.exclude_top as string) : undefined

  const filterClauses: ReturnType<typeof sql>[] = []
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
    const ftsMatch = search.split(/\s+/).filter(Boolean).map(w => `"${w.replace(/"/g, '')}"`).join(' ')
    const extraWhere = filterClauses.length > 0
      ? sql` AND ${sql.join(filterClauses, sql` AND `)}`
      : sql``

    // Get all jornais with their M/F counts, ranked by proportion of target gender
    const rows = await db.all<{ name: string; gender: string; count: number }>(sql`
      SELECT j.nome as name, q.gender, count(*) as count
      FROM noticias_fts
      JOIN noticias n ON n.rowid = noticias_fts.rowid
      JOIN quotes q ON q.noticia_id = n.id
      JOIN jornais j ON n.jornal_id = j.id
      WHERE noticias_fts MATCH ${ftsMatch} ${extraWhere}
        ${excludeClause}
        AND j.nome IS NOT NULL
      GROUP BY j.nome, q.gender
    `)

    // Get article counts per jornal
    const articleRows = await db.all<{ name: string; articles: number }>(sql`
      SELECT j.nome as name, count(DISTINCT n.id) as articles
      FROM noticias_fts
      JOIN noticias n ON n.rowid = noticias_fts.rowid
      JOIN jornais j ON n.jornal_id = j.id
      WHERE noticias_fts MATCH ${ftsMatch} ${extraWhere}
        AND j.nome IS NOT NULL
      GROUP BY j.nome
    `)

    return { jornais: buildResult(rows, articleRows, gender, limit) }
  }

  // Non-FTS path
  const extraWhere = filterClauses.length > 0
    ? sql`AND ${sql.join(filterClauses, sql` AND `)}`
    : sql``

  const rows = await db.all<{ name: string; gender: string; count: number }>(sql`
    SELECT j.nome as name, q.gender, count(*) as count
    FROM quotes q
    JOIN noticias n ON q.noticia_id = n.id
    JOIN jornais j ON n.jornal_id = j.id
    WHERE j.nome IS NOT NULL ${excludeClause} ${extraWhere}
    GROUP BY j.nome, q.gender
  `)

  const articleRows = await db.all<{ name: string; articles: number }>(sql`
    SELECT j.nome as name, count(DISTINCT n.id) as articles
    FROM noticias n
    JOIN jornais j ON n.jornal_id = j.id
    WHERE j.nome IS NOT NULL ${extraWhere}
    GROUP BY j.nome
  `)

  return { jornais: buildResult(rows, articleRows, gender, limit) }
})

function buildResult(
  rows: { name: string; gender: string; count: number }[],
  articleRows: { name: string; articles: number }[],
  targetGender: string,
  limit: number,
) {
  // Build per-jornal M/F counts
  const map: Record<string, { M: number; F: number }> = {}
  for (const r of rows) {
    if (!map[r.name]) map[r.name] = { M: 0, F: 0 }
    if (r.gender === 'M') map[r.name].M = r.count
    else if (r.gender === 'F') map[r.name].F = r.count
  }

  // Article counts
  const articleMap: Record<string, number> = {}
  for (const r of articleRows) articleMap[r.name] = r.articles

  // Filter: min 30 citations total to avoid noise
  const MIN_CITATIONS = 30
  const eligible = Object.entries(map)
    .filter(([_, counts]) => (counts.M + counts.F) >= MIN_CITATIONS)

  // Sort by proportion of target gender
  eligible.sort(([_, a], [__, b]) => {
    const aTotal = a.M + a.F
    const bTotal = b.M + b.F
    const aRatio = targetGender === 'F' ? a.F / aTotal : a.M / aTotal
    const bRatio = targetGender === 'F' ? b.F / bTotal : b.M / bTotal
    return bRatio - aRatio
  })

  return eligible.slice(0, limit).map(([name, counts]) => ({
    name,
    M: counts.M,
    F: counts.F,
    articles: articleMap[name] || 0,
  }))
}
