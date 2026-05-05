import { sql } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  const db = useDB(event)
  const query = getQuery(event)

  const field = query.field as string | undefined
  const q = (query.q as string || '').trim()

  if (field === 'jornal') {
    // Jornais table is small — return all names, optionally filtered
    const filter = q ? sql`AND j.nome LIKE ${`%${q}%`}` : sql``
    const distrito = query.distrito as string | undefined
    const distritoJoin = distrito
      ? sql`JOIN jornais_distritos jd ON jd.jornal_id = j.id`
      : sql``
    const distritoFilter = distrito
      ? sql`AND jd.distrito_codigoine = ${distrito}`
      : sql``
    const rows = await db.all<{ name: string; count: number }>(sql`
      SELECT j.nome as name, count(n.id) as count
      FROM jornais j
      ${distritoJoin}
      LEFT JOIN noticias n ON n.jornal_id = j.id
      WHERE j.nome IS NOT NULL ${filter} ${distritoFilter}
      GROUP BY j.nome
      ORDER BY count DESC
      LIMIT 50
    `)
    return rows
  }

  if (field === 'author') {
    if (q.length < 3) return []
    const rows = await db.all<{ name: string; count: number }>(sql`
      SELECT author as name, count(*) as count
      FROM noticias
      WHERE author IS NOT NULL AND author LIKE ${`%${q}%`}
      GROUP BY author
      ORDER BY count DESC
      LIMIT 20
    `)
    return rows
  }

  return []
})
