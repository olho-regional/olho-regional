import { sql } from 'drizzle-orm'

/**
 * GET /api/analises/gender-map?gender=M&year_from=...&year_to=...&search=...
 *
 * Returns district-level counts broken down by year for a specific gender.
 * Heavy query — only used during static compilation of analises, NOT by the live dashboard.
 *
 * Response: { years: string[], districts: Record<string, Record<string, number>> }
 *   districts[districtName][year] = count
 */
export default defineEventHandler(async (event) => {
  const db = useDB(event)
  const query = getQuery(event)

  const gender = query.gender as string | undefined
  const search = query.search as string | undefined
  const yearFrom = query.year_from as string | undefined
  const yearTo = query.year_to as string | undefined
  const distrito = query.distrito as string | undefined

  if (!gender) {
    throw createError({ statusCode: 400, statusMessage: 'gender parameter required (M or F)' })
  }

  const filterClauses: ReturnType<typeof sql>[] = []
  filterClauses.push(sql`q.gender = ${gender}`)
  if (yearFrom) filterClauses.push(sql`n.date >= ${`${yearFrom}-01-01`}`)
  if (yearTo) filterClauses.push(sql`n.date <= ${`${yearTo}-12-31`}`)
  if (distrito) filterClauses.push(sql`jd.distrito_codigoine = ${distrito}`)
  filterClauses.push(sql`n.date IS NOT NULL AND length(n.date) >= 4`)

  if (search) {
    const ftsMatch = search.split(/\s+/).filter(Boolean).map(w => `"${w.replace(/"/g, '')}"`).join(' ')

    const rows = await db.all<{ year: string; district: string; count: number }>(sql`
      SELECT
        substr(n.date, 1, 4) as year,
        d.nome as district,
        count(*) as count
      FROM noticias_fts
      JOIN noticias n ON n.rowid = noticias_fts.rowid
      JOIN quotes q ON q.noticia_id = n.id
      LEFT JOIN jornais j ON n.jornal_id = j.id
      JOIN jornais_distritos jd ON jd.jornal_id = j.id
      JOIN distritos d ON d.codigoine = jd.distrito_codigoine
      WHERE noticias_fts MATCH ${ftsMatch}
        AND ${sql.join(filterClauses, sql` AND `)}
      GROUP BY year, d.nome
      ORDER BY year, d.nome
    `)

    return buildResponse(rows)
  }

  // Non-FTS path
  const rows = await db.all<{ year: string; district: string; count: number }>(sql`
    SELECT
      substr(n.date, 1, 4) as year,
      d.nome as district,
      count(*) as count
    FROM noticias n
    JOIN quotes q ON q.noticia_id = n.id
    LEFT JOIN jornais j ON n.jornal_id = j.id
    JOIN jornais_distritos jd ON jd.jornal_id = j.id
    JOIN distritos d ON d.codigoine = jd.distrito_codigoine
    WHERE ${sql.join(filterClauses, sql` AND `)}
    GROUP BY year, d.nome
    ORDER BY year, d.nome
  `)

  return buildResponse(rows)
})

function buildResponse(rows: { year: string; district: string; count: number }[]) {
  const years = [...new Set(rows.map(r => r.year))].sort()
  const districts: Record<string, Record<string, number>> = {}

  for (const row of rows) {
    if (!districts[row.district]) districts[row.district] = {}
    districts[row.district][row.year] = row.count
  }

  return { years, districts }
}
