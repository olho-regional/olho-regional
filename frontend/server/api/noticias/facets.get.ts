import { sql } from 'drizzle-orm'

/**
 * GET /api/noticias/facets
 *
 * Returns aggregation facets (labelCounts, jornalCounts, distritoCounts, genderByYear, dateCounts)
 * for the current filter set. Called lazily by the frontend to avoid computing everything on initial load.
 *
 * Query params: same filters as /api/noticias (search, distrito, jornal, author, year_from, year_to)
 *   + include: comma-separated list of facets to include (default: labels,jornais,distritos,gender)
 *              add "calendar" to include dateCounts (expensive)
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
  const include = ((query.include as string) || 'labels,jornais,distritos,gender').split(',')

  const distritoJoin = distrito
    ? sql`JOIN jornais_distritos jd ON jd.jornal_id = j.id`
    : sql``

  // Build filter conditions
  const filterClauses: ReturnType<typeof sql>[] = []
  if (distrito) filterClauses.push(sql`jd.distrito_codigoine = ${distrito}`)
  if (jornal) filterClauses.push(sql`j.nome = ${jornal}`)
  if (author) filterClauses.push(sql`n.author = ${author}`)
  if (yearFrom) filterClauses.push(sql`n.date >= ${`${yearFrom}-01-01`}`)
  if (yearTo) filterClauses.push(sql`n.date <= ${`${yearTo}-12-31`}`)

  // FTS path
  if (search) {
    const ftsMatch = search.split(/\s+/).filter(Boolean).map(w => `"${w.replace(/"/g, '')}"`).join(' ')
    const extraWhere = filterClauses.length > 0
      ? sql` AND ${sql.join(filterClauses, sql` AND `)}`
      : sql``

    const result: Record<string, any> = {}

    const promises: Promise<void>[] = []

    if (include.includes('labels')) {
      promises.push(db.all<{ name: string; count: number }>(sql`
        SELECT l.name, count(DISTINCT n.id) as count
        FROM noticias_fts
        JOIN noticias n ON n.rowid = noticias_fts.rowid
        JOIN noticias_labels nl ON nl.noticia_id = n.id
        JOIN labels l ON nl.label_id = l.id
        LEFT JOIN jornais j ON n.jornal_id = j.id
        ${distritoJoin}
        WHERE noticias_fts MATCH ${ftsMatch} ${extraWhere}
        GROUP BY l.name ORDER BY count DESC
      `).then(r => { result.labelCounts = r }))
    }

    if (include.includes('jornais')) {
      promises.push(db.all<{ name: string; count: number }>(sql`
        SELECT j.nome as name, count(DISTINCT n.id) as count
        FROM noticias_fts
        JOIN noticias n ON n.rowid = noticias_fts.rowid
        LEFT JOIN jornais j ON n.jornal_id = j.id
        ${distritoJoin}
        WHERE noticias_fts MATCH ${ftsMatch} ${extraWhere}
          AND j.nome IS NOT NULL
        GROUP BY j.nome ORDER BY count DESC
        LIMIT 30
      `).then(r => { result.jornalCounts = r }))
    }

    if (include.includes('distritos')) {
      promises.push(db.all<{ name: string; count: number }>(sql`
        SELECT d2.nome as name, count(DISTINCT n.id) as count
        FROM noticias_fts
        JOIN noticias n ON n.rowid = noticias_fts.rowid
        LEFT JOIN jornais j ON n.jornal_id = j.id
        JOIN jornais_distritos jd2 ON jd2.jornal_id = j.id
        JOIN distritos d2 ON d2.codigoine = jd2.distrito_codigoine
        ${distrito ? sql`${distritoJoin}` : sql``}
        WHERE noticias_fts MATCH ${ftsMatch} ${extraWhere}
        Group BY d2.nome ORDER BY count DESC
      `).then(r => { result.distritoCounts = r }))
    }

    if (include.includes('gender')) {
      promises.push(db.all<{ year: string; gender: string; count: number }>(sql`
        SELECT substr(n.date, 1, 4) as year, q.gender, count(*) as count
        FROM noticias_fts
        JOIN noticias n ON n.rowid = noticias_fts.rowid
        JOIN quotes q ON q.noticia_id = n.id
        LEFT JOIN jornais j ON n.jornal_id = j.id
        ${distritoJoin}
        WHERE noticias_fts MATCH ${ftsMatch} ${extraWhere}
          AND n.date IS NOT NULL AND length(n.date) >= 4
        GROUP BY year, q.gender ORDER BY year
      `).then(r => { result.genderByYear = r }))
    }

    if (include.includes('calendar')) {
      promises.push(db.all<{ date: string; count: number }>(sql`
        SELECT substr(n.date, 1, 10) as date, count(DISTINCT n.id) as count
        FROM noticias_fts
        JOIN noticias n ON n.rowid = noticias_fts.rowid
        LEFT JOIN jornais j ON n.jornal_id = j.id
        ${distritoJoin}
        WHERE noticias_fts MATCH ${ftsMatch} ${extraWhere}
          AND n.date IS NOT NULL AND length(n.date) >= 10
        GROUP BY date ORDER BY date
      `).then(r => { result.dateCounts = r }))
    }

    await Promise.all(promises)
    return result
  }

  // Non-FTS path: use pre-aggregated summary tables (drastically fewer row reads)
  // Filter by year range on summary tables
  const yearFilter = (yearFrom || yearTo)
    ? sql`${yearFrom ? sql`s.year >= ${yearFrom}` : sql`1=1`} AND ${yearTo ? sql`s.year <= ${yearTo}` : sql`1=1`}`
    : sql`1=1`

  // Filter by distrito via jornal junction
  const distritoStatJoin = distrito
    ? sql`JOIN jornais_distritos jd ON jd.jornal_id = s.jornal_id`
    : sql``
  const distritoStatFilter = distrito
    ? sql`AND jd.distrito_codigoine = ${distrito}`
    : sql``

  // Filter by jornal name
  const jornalStatJoin = jornal
    ? sql`JOIN jornais j ON j.id = s.jornal_id`
    : sql``
  const jornalStatFilter = jornal
    ? sql`AND j.nome = ${jornal}`
    : sql``

  // If author is specified, we can't use summary tables (no author dimension)
  // Fall back to scanning noticias for that case
  if (author) {
    const jJoin = sql`LEFT JOIN jornais j ON n.jornal_id = j.id`
    const filterClauses2: ReturnType<typeof sql>[] = []
    if (distrito) filterClauses2.push(sql`jd.distrito_codigoine = ${distrito}`)
    if (jornal) filterClauses2.push(sql`j.nome = ${jornal}`)
    filterClauses2.push(sql`n.author = ${author}`)
    if (yearFrom) filterClauses2.push(sql`n.date >= ${`${yearFrom}-01-01`}`)
    if (yearTo) filterClauses2.push(sql`n.date <= ${`${yearTo}-12-31`}`)
    const dateWhereClause = sql`AND ${sql.join(filterClauses2, sql` AND `)}`

    const result: Record<string, any> = {}
    const promises: Promise<void>[] = []

    if (include.includes('labels')) {
      promises.push(db.all(sql`
        SELECT l.name, count(DISTINCT n.id) as count
        FROM noticias n
        JOIN noticias_labels nl ON nl.noticia_id = n.id
        JOIN labels l ON nl.label_id = l.id
        ${jJoin} ${distritoStatJoin}
        WHERE 1=1 ${dateWhereClause}
        GROUP BY l.name ORDER BY count DESC
      `).then((r: any) => { result.labelCounts = r }))
    }
    if (include.includes('jornais')) {
      promises.push(db.all(sql`
        SELECT j2.nome as name, count(DISTINCT n.id) as count
        FROM noticias n
        JOIN jornais j2 ON n.jornal_id = j2.id
        ${distritoStatJoin}
        WHERE j2.nome IS NOT NULL ${dateWhereClause}
        GROUP BY j2.nome ORDER BY count DESC LIMIT 30
      `).then((r: any) => { result.jornalCounts = r }))
    }
    if (include.includes('distritos')) {
      promises.push(db.all(sql`
        SELECT d2.nome as name, count(DISTINCT n.id) as count
        FROM noticias n
        JOIN jornais j2 ON n.jornal_id = j2.id
        JOIN jornais_distritos jd2 ON jd2.jornal_id = j2.id
        JOIN distritos d2 ON d2.codigoine = jd2.distrito_codigoine
        WHERE 1=1 ${dateWhereClause}
        GROUP BY d2.nome ORDER BY count DESC
      `).then((r: any) => { result.distritoCounts = r }))
    }
    if (include.includes('gender')) {
      promises.push(db.all(sql`
        SELECT substr(n.date, 1, 4) as year, q.gender, count(*) as count
        FROM noticias n
        JOIN quotes q ON q.noticia_id = n.id
        ${jJoin} ${distritoStatJoin}
        WHERE n.date IS NOT NULL AND length(n.date) >= 4 ${dateWhereClause}
        GROUP BY year, q.gender ORDER BY year
      `).then((r: any) => { result.genderByYear = r }))
    }
    if (include.includes('calendar')) {
      promises.push(db.all(sql`
        SELECT substr(n.date, 1, 10) as date, count(DISTINCT n.id) as count
        FROM noticias n
        ${jJoin} ${distritoStatJoin}
        WHERE n.date IS NOT NULL AND length(n.date) >= 10 ${dateWhereClause}
        GROUP BY date ORDER BY date
      `).then((r: any) => { result.dateCounts = r }))
    }

    await Promise.all(promises)
    return result
  }

  // Summary table path (no author filter, no FTS)
  const result: Record<string, any> = {}
  const promises: Promise<void>[] = []

  if (include.includes('labels')) {
    promises.push(db.all(sql`
      SELECT l.name, SUM(s.count) as count
      FROM stats_year_label s
      JOIN labels l ON l.id = s.label_id
      ${distritoStatJoin}
      ${jornalStatJoin}
      WHERE ${yearFilter} ${distritoStatFilter} ${jornalStatFilter}
      GROUP BY l.name ORDER BY count DESC
    `).then((r: any) => { result.labelCounts = r }))
  }

  if (include.includes('jornais')) {
    promises.push(db.all(sql`
      SELECT j2.nome as name, SUM(s.count) as count
      FROM stats_year_jornal s
      JOIN jornais j2 ON j2.id = s.jornal_id
      ${distritoStatJoin}
      ${jornalStatJoin}
      WHERE ${yearFilter} ${distritoStatFilter} ${jornalStatFilter}
        AND j2.nome IS NOT NULL
      GROUP BY j2.nome ORDER BY count DESC
      LIMIT 30
    `).then((r: any) => { result.jornalCounts = r }))
  }

  if (include.includes('distritos')) {
    promises.push(db.all(sql`
      SELECT d2.nome as name, SUM(s.count) as count
      FROM stats_year_jornal s
      JOIN jornais_distritos jd2 ON jd2.jornal_id = s.jornal_id
      JOIN distritos d2 ON d2.codigoine = jd2.distrito_codigoine
      ${distritoStatJoin}
      ${jornalStatJoin}
      WHERE ${yearFilter} ${distritoStatFilter} ${jornalStatFilter}
      GROUP BY d2.nome ORDER BY count DESC
    `).then((r: any) => { result.distritoCounts = r }))
  }

  if (include.includes('gender')) {
    promises.push(db.all(sql`
      SELECT s.year, s.gender, SUM(s.count) as count
      FROM stats_year_gender s
      ${distritoStatJoin}
      ${jornalStatJoin}
      WHERE ${yearFilter} ${distritoStatFilter} ${jornalStatFilter}
      GROUP BY s.year, s.gender ORDER BY s.year
    `).then((r: any) => { result.genderByYear = r }))
  }

  if (include.includes('calendar')) {
    // Use date-level summary table
    const dateFilter = (yearFrom || yearTo)
      ? sql`${yearFrom ? sql`s.date >= ${`${yearFrom}-01-01`}` : sql`1=1`} AND ${yearTo ? sql`s.date <= ${`${yearTo}-12-31`}` : sql`1=1`}`
      : sql`1=1`
    const distritoDateJoin = distrito
      ? sql`JOIN jornais_distritos jd ON jd.jornal_id = s.jornal_id`
      : sql``
    const distritoDateFilter = distrito
      ? sql`AND jd.distrito_codigoine = ${distrito}`
      : sql``
    const jornalDateJoin = jornal
      ? sql`JOIN jornais j ON j.id = s.jornal_id`
      : sql``
    const jornalDateFilter = jornal
      ? sql`AND j.nome = ${jornal}`
      : sql``

    promises.push(db.all(sql`
      SELECT s.date, SUM(s.count) as count
      FROM stats_date_jornal s
      ${distritoDateJoin}
      ${jornalDateJoin}
      WHERE ${dateFilter} ${distritoDateFilter} ${jornalDateFilter}
      GROUP BY s.date ORDER BY s.date
    `).then((r: any) => { result.dateCounts = r }))
  }

  await Promise.all(promises)
  return result
})
