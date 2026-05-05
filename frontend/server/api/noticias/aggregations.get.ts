import { sql } from 'drizzle-orm'

/**
 * Cached aggregation data for the default (unfiltered) view.
 * Returns yearCounts, labelCounts, jornalCounts, distritoCounts, dateCounts.
 * Only changes on DB rebuild — cached for 30 days.
 */
export default defineCachedEventHandler(async (event) => {
  const db = useDB(event)

  const [yearCounts, labelCounts, jornalCounts, distritoCounts, dateCounts, genderByYear, distritoCountsByYear] = await Promise.all([
    db.all<{ year: string; count: number }>(sql`
      SELECT substr(date, 1, 4) as year, count(*) as count
      FROM noticias
      WHERE date IS NOT NULL AND length(date) >= 4
      GROUP BY year ORDER BY year
    `),
    db.all<{ name: string; count: number }>(sql`
      SELECT l.name, count(*) as count
      FROM noticias_labels nl
      JOIN labels l ON nl.label_id = l.id
      GROUP BY l.name ORDER BY count DESC
    `),
    db.all<{ name: string; count: number }>(sql`
      SELECT j.nome as name, count(*) as count
      FROM noticias n
      JOIN jornais j ON n.jornal_id = j.id
      WHERE j.nome IS NOT NULL
      GROUP BY j.nome ORDER BY count DESC
      LIMIT 30
    `),
    db.all<{ name: string; count: number }>(sql`
      SELECT d.nome as name, count(DISTINCT n.id) as count
      FROM noticias n
      JOIN jornais j ON n.jornal_id = j.id
      JOIN jornais_distritos jd ON jd.jornal_id = j.id
      JOIN distritos d ON d.codigoine = jd.distrito_codigoine
      GROUP BY d.nome ORDER BY count DESC
    `),
    db.all<{ date: string; count: number }>(sql`
      SELECT substr(date, 1, 10) as date, count(*) as count
      FROM noticias
      WHERE date IS NOT NULL AND length(date) >= 10
      GROUP BY date ORDER BY date
    `),
    db.all<{ year: string; gender: string; count: number }>(sql`
      SELECT substr(n.date, 1, 4) as year, q.gender, count(*) as count
      FROM quotes q
      JOIN noticias n ON n.id = q.noticia_id
      WHERE n.date IS NOT NULL AND length(n.date) >= 4
      GROUP BY year, q.gender ORDER BY year
    `),
    db.all<{ year: string; name: string; count: number }>(sql`
      SELECT s.year, d.nome as name, SUM(s.count) as count
      FROM stats_year_jornal s
      JOIN jornais_distritos jd ON jd.jornal_id = s.jornal_id
      JOIN distritos d ON d.codigoine = jd.distrito_codigoine
      WHERE length(s.year) = 4 AND s.year GLOB '[0-9][0-9][0-9][0-9]'
      GROUP BY s.year, d.nome ORDER BY s.year
    `),
  ])

  const total = (await db.get<{ total: number }>(sql`SELECT count(*) as total FROM noticias`))?.total ?? 0

  return { total, yearCounts, labelCounts, jornalCounts, distritoCounts, dateCounts, genderByYear, distritoCountsByYear }
}, {
  maxAge: 60 * 60 * 24 * 3,
  swr: true,
  name: 'aggregations-default',
})
