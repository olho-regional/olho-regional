import { sql } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  const db = useDB(event)

  const rows = await db.all<{ nome: string; url: string | null; distrito: string }>(sql`
    SELECT j.nome, j.url, d.nome as distrito
    FROM jornais j
    JOIN jornais_distritos jd ON jd.jornal_id = j.id
    JOIN distritos d ON d.codigoine = jd.distrito_codigoine
    ORDER BY d.nome, j.nome
  `)

  // Group by distrito
  const grouped: Record<string, { nome: string; url: string | null }[]> = {}
  for (const row of rows) {
    const key = row.distrito
    if (!grouped[key]) grouped[key] = []
    grouped[key].push({ nome: row.nome, url: row.url })
  }

  return grouped
})
