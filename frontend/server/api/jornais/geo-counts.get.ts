import { sql } from 'drizzle-orm'

/**
 * Cached jornal counts by distrito and município.
 * Used by the homepage choropleth maps.
 */
export default defineCachedEventHandler(async (event) => {
  const db = useDB(event)

  const [districtRows, concelhoRows] = await Promise.all([
    db.all<{ name: string; count: number }>(sql`
      SELECT d.nome as name, count(DISTINCT jd.jornal_id) as count
      FROM jornais_distritos jd
      JOIN distritos d ON d.codigoine = jd.distrito_codigoine
      GROUP BY d.nome ORDER BY count DESC
    `),
    // Count per município: direct links + inherited distrito coverage
    // Município codigoine starts with its distrito code (e.g. "0201" → distrito "02"),
    // so substr gives us the parent distrito directly — no extra JOIN needed.
    // No overlap: inherited set only includes jornais with zero município links.
    db.all<{ name: string; count: number }>(sql`
      SELECT name, count FROM (
        SELECT m.nome as name,
          (SELECT count(DISTINCT jornal_id) FROM jornais_municipios WHERE municipio_codigoine = m.codigoine)
          + (SELECT count(*) FROM jornais_distritos jd
             WHERE jd.distrito_codigoine = substr(m.codigoine, 1, 2)
             AND NOT EXISTS (SELECT 1 FROM jornais_municipios jm WHERE jm.jornal_id = jd.jornal_id))
          as count
        FROM municipios m
      ) WHERE count > 0
      ORDER BY count DESC
    `),
  ])

  const districtCounts: Record<string, number> = {}
  for (const r of districtRows) districtCounts[r.name] = r.count

  const concelhoCounts: Record<string, number> = {}
  for (const r of concelhoRows) concelhoCounts[r.name] = r.count

  return { districtCounts, concelhoCounts }
}, { maxAge: 60 * 60 * 24 * 30 })
