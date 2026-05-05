import { sql } from 'drizzle-orm'

/**
 * Cached jornal counts by município — only active jornais (estado = 'Ativo').
 * Used by the "desertos noticiosos" section on the homepage.
 */
export default defineCachedEventHandler(async (event) => {
  const db = useDB(event)

  const concelhoRows = await db.all<{ name: string; count: number }>(sql`
    SELECT m.nome as name, count(DISTINCT jm.jornal_id) as count
    FROM municipios m
    JOIN jornais_municipios jm ON jm.municipio_codigoine = m.codigoine
    JOIN jornais j ON j.id = jm.jornal_id
    WHERE lower(j.estado) = 'ativo'
    GROUP BY m.codigoine
    HAVING count > 0
    ORDER BY count DESC
  `)

  const concelhoCounts: Record<string, number> = {}
  for (const r of concelhoRows) concelhoCounts[r.name] = r.count

  return { concelhoCounts }
}, { maxAge: 60 * 60 * 24 * 30 })
