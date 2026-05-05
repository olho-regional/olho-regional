import { sql } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  const db = useDB(event)
  const query = getQuery(event)

  const search = query.search as string | undefined
  const distrito = query.distrito as string | undefined
  const jornal = query.jornal as string | undefined
  const author = query.author as string | undefined
  const yearFrom = query.year_from as string | undefined
  const yearTo = query.year_to as string | undefined
  const page = Math.max(1, parseInt(query.page as string) || 1)
  const perPage = Math.min(100, Math.max(1, parseInt(query.per_page as string) || 20))
  const offset = (page - 1) * perPage

  // distrito filter: find noticias whose jornal covers a given distrito (by codigoine)
  const distritoJoin = distrito
    ? sql`JOIN jornais_distritos jd ON jd.jornal_id = j.id`
    : sql``
  const distritoFilter = distrito ? sql`jd.distrito_codigoine = ${distrito}` : null

  // When searching, use FTS5 for performance
  if (search) {
    const ftsMatch = search.split(/\s+/).filter(Boolean).map(w => `"${w.replace(/"/g, '')}"`).join(' ')

    const filterClauses: ReturnType<typeof sql>[] = []
    if (distritoFilter) filterClauses.push(distritoFilter)
    if (jornal) filterClauses.push(sql`j.nome = ${jornal}`)
    if (author) filterClauses.push(sql`n.author = ${author}`)
    if (yearFrom) filterClauses.push(sql`n.date >= ${`${yearFrom}-01-01`}`)
    if (yearTo) filterClauses.push(sql`n.date <= ${`${yearTo}-12-31`}`)

    const extraWhere = filterClauses.length > 0
      ? sql` AND ${sql.join(filterClauses, sql` AND `)}`
      : sql``

    const [totalResult, items, yearCounts] = await Promise.all([
      db.get<{ total: number }>(sql`
        SELECT count(DISTINCT n.id) as total
        FROM noticias_fts
        JOIN noticias n ON n.rowid = noticias_fts.rowid
        LEFT JOIN jornais j ON n.jornal_id = j.id
        ${distritoJoin}
        WHERE noticias_fts MATCH ${ftsMatch} ${extraWhere}
      `),
      db.all<{
        id: string; title: string | null; date: string | null; author: string | null
        url: string; archive_url: string | null; jornal_nome: string | null
      }>(sql`
        SELECT DISTINCT n.id, n.title, n.date, n.author, n.url, n.archive_url,
               j.nome as jornal_nome
        FROM noticias_fts
        JOIN noticias n ON n.rowid = noticias_fts.rowid
        LEFT JOIN jornais j ON n.jornal_id = j.id
        ${distritoJoin}
        WHERE noticias_fts MATCH ${ftsMatch} ${extraWhere}
        ORDER BY rank
        LIMIT ${perPage} OFFSET ${offset}
      `),
      db.all<{ year: string; count: number }>(sql`
        SELECT substr(n.date, 1, 4) as year, count(DISTINCT n.id) as count
        FROM noticias_fts
        JOIN noticias n ON n.rowid = noticias_fts.rowid
        LEFT JOIN jornais j ON n.jornal_id = j.id
        ${distritoJoin}
        WHERE noticias_fts MATCH ${ftsMatch} ${extraWhere}
          AND n.date IS NOT NULL AND length(n.date) >= 4
        GROUP BY year ORDER BY year
      `),
    ])

    const total = totalResult?.total ?? 0
    return { items, total, page, perPage, totalPages: Math.ceil(total / perPage), yearCounts }
  }

  // Non-search queries use raw SQL for distrito filtering
  const hasAnyFilter = !!distrito || !!jornal || !!author ||
    (yearFrom && parseInt(yearFrom) > 1996) || (yearTo && parseInt(yearTo) < 2026)

  // Build filter conditions for raw SQL (needed for items query)
  const filterClauses: ReturnType<typeof sql>[] = []
  if (distrito) filterClauses.push(sql`jd.distrito_codigoine = ${distrito}`)
  if (jornal) filterClauses.push(sql`j.nome = ${jornal}`)
  if (author) filterClauses.push(sql`n.author = ${author}`)
  if (yearFrom) filterClauses.push(sql`n.date >= ${`${yearFrom}-01-01`}`)
  if (yearTo) filterClauses.push(sql`n.date <= ${`${yearTo}-12-31`}`)

  const whereClause = filterClauses.length > 0
    ? sql`WHERE ${sql.join(filterClauses, sql` AND `)}`
    : sql``

  const jJoin = sql`LEFT JOIN jornais j ON n.jornal_id = j.id`

  // Items always come from noticias (need actual row data)
  const items = await db.all<{
    id: string; title: string | null; date: string | null; author: string | null
    url: string; archive_url: string | null; jornal_nome: string | null
  }>(sql`
    SELECT DISTINCT n.id, n.title, n.date, n.author, n.url, n.archive_url,
           j.nome as jornal_nome
    FROM noticias n
    ${jJoin}
    ${distritoJoin}
    ${whereClause}
    ORDER BY n.date DESC
    LIMIT ${perPage} OFFSET ${offset}
  `)

  // If no filters active, use cached aggregations for total + yearCounts
  if (!hasAnyFilter) {
    const cached = await $fetch('/api/noticias/aggregations') as { total: number; yearCounts: { year: string; count: number }[] }
    return {
      items,
      total: cached.total,
      page,
      perPage,
      totalPages: Math.ceil(cached.total / perPage),
      yearCounts: cached.yearCounts,
    }
  }

  // Use summary tables for total + yearCounts when no author filter
  // (author is not a dimension in summary tables)
  if (!author) {
    const yearFilter = (yearFrom || yearTo)
      ? sql`${yearFrom ? sql`s.year >= ${yearFrom}` : sql`1=1`} AND ${yearTo ? sql`s.year <= ${yearTo}` : sql`1=1`}`
      : sql`1=1`
    const distritoStatJoin = distrito
      ? sql`JOIN jornais_distritos jd ON jd.jornal_id = s.jornal_id`
      : sql``
    const distritoStatFilter = distrito
      ? sql`AND jd.distrito_codigoine = ${distrito}`
      : sql``
    const jornalStatJoin = jornal
      ? sql`JOIN jornais j ON j.id = s.jornal_id`
      : sql``
    const jornalStatFilter = jornal
      ? sql`AND j.nome = ${jornal}`
      : sql``

    const [totalResult, yearCounts] = await Promise.all([
      db.get(sql`
        SELECT SUM(s.count) as total
        FROM stats_year_jornal s
        ${distritoStatJoin}
        ${jornalStatJoin}
        WHERE ${yearFilter} ${distritoStatFilter} ${jornalStatFilter}
      `) as Promise<{ total: number } | undefined>,
      db.all(sql`
        SELECT s.year, SUM(s.count) as count
        FROM stats_year_jornal s
        ${distritoStatJoin}
        ${jornalStatJoin}
        WHERE ${yearFilter} ${distritoStatFilter} ${jornalStatFilter}
        GROUP BY s.year ORDER BY s.year
      `) as Promise<{ year: string; count: number }[]>,
    ])

    const total = (totalResult as any)?.total ?? 0
    return { items, total, page, perPage, totalPages: Math.ceil(total / perPage), yearCounts }
  }

  // Fallback: author filter requires scanning noticias
  const [totalResult, yearCounts] = await Promise.all([
    db.get(sql`
      SELECT count(DISTINCT n.id) as total
      FROM noticias n
      ${jJoin}
      ${distritoJoin}
      ${whereClause}
    `) as Promise<{ total: number } | undefined>,
    db.all(sql`
      SELECT substr(n.date, 1, 4) as year, count(DISTINCT n.id) as count
      FROM noticias n
      ${jJoin}
      ${distritoJoin}
      WHERE n.date IS NOT NULL AND length(n.date) >= 4
        AND ${sql.join(filterClauses, sql` AND `)}
      GROUP BY year ORDER BY year
    `) as Promise<{ year: string; count: number }[]>,
  ])

  const total = (totalResult as any)?.total ?? 0

  return {
    items,
    total,
    page,
    perPage,
    totalPages: Math.ceil(total / perPage),
    yearCounts,
  }
})
